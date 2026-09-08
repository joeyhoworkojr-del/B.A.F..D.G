import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { GameChat } from './GameChat'
import { DriveFeed } from '../game/DriveFeed'
import { api } from '../../api/client'
import { SessionProvider } from '../../session/SessionProvider'
import type { ChatMessage, ChatPage, PlayOut } from '../../types'

function message(over: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: 'm1', seq: 1, user_id: 'u2', username: 'other', display_name: 'Other',
    avatar_url: '', text: 'Buffalo look sharp', created_at: new Date().toISOString(),
    system: false, reply_to: null, reply_preview: '', reactions: {},
    deleted: false, hidden: false, mine: false, ...over,
  }
}

function page(over: Partial<ChatPage> = {}): ChatPage {
  return {
    game_id: 'nfl:1', messages: [message()], cursor: 1, count: 1,
    signed_in: true, may_post: true, blocked_reason: '',
    reactions_available: ['👍', '🔥'], ...over,
  }
}

const signedIn = {
  user: {
    id: 'u1', username: 'fan', display_name: 'Fan', bio: '', avatar_url: '',
    favourite_sports: [], favourite_teams: [], badges: [],
    created_at: '2026-01-01T00:00:00Z', email: 'f@e.com', email_verified: false,
    level: 'beta', interests: [], onboarded: true, profile_public: true,
  },
  entitlements: {
    level: 'beta', powers: [], authenticated: true, beta_open: true,
    features: {}, unavailable_reason: {}, billing_enabled: false, note: '',
  },
}

beforeEach(() => {
  // EventSource does not exist in jsdom; the hook must fall back to polling
  // rather than throwing, which is the same path a buffering proxy produces.
  vi.stubGlobal('EventSource', undefined)
})
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals() })

function renderChat() {
  return render(
    <SessionProvider>
      <MemoryRouter><GameChat league="nfl" eventId="1" /></MemoryRouter>
    </SessionProvider>,
  )
}

describe('Game chat', () => {
  it('renders messages without an EventSource, falling back cleanly', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(signedIn as never)
    vi.spyOn(api, 'chat').mockResolvedValue(page())
    renderChat()
    expect(await screen.findByText('Buffalo look sharp')).toBeInTheDocument()
  })

  it('never renders message text as markup', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(signedIn as never)
    vi.spyOn(api, 'chat').mockResolvedValue(
      page({ messages: [message({ text: '<img src=x onerror=alert(1)>' })] }),
    )
    const { container } = renderChat()
    // The tag arrives as text and stays text — no element is created from it.
    expect(await screen.findByText('<img src=x onerror=alert(1)>')).toBeInTheDocument()
    expect(container.querySelector('img[onerror]')).toBeNull()
  })

  it('shows a deleted message as removed rather than showing its text', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(signedIn as never)
    vi.spyOn(api, 'chat').mockResolvedValue(
      page({ messages: [message({ deleted: true, text: '' })] }),
    )
    renderChat()
    expect(await screen.findByText(/message deleted/i)).toBeInTheDocument()
  })

  it('distinguishes hidden-pending-review from deleted', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(signedIn as never)
    vi.spyOn(api, 'chat').mockResolvedValue(
      page({ messages: [message({ hidden: true, text: '' })] }),
    )
    renderChat()
    expect(await screen.findByText(/pending review/i)).toBeInTheDocument()
  })

  it('asks a signed-out visitor to log in but still shows the room', async () => {
    vi.spyOn(api, 'session').mockResolvedValue({
      user: null,
      entitlements: { level: 'guest', powers: [], authenticated: false, beta_open: true,
                      features: {}, unavailable_reason: {}, billing_enabled: false, note: '' },
    } as never)
    vi.spyOn(api, 'chat').mockResolvedValue(page({ signed_in: false, may_post: false }))
    renderChat()
    expect(await screen.findByText('Buffalo look sharp')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /log in/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /send/i })).not.toBeInTheDocument()
  })

  it('tells a muted user why they cannot post, in the server’s words', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(signedIn as never)
    vi.spyOn(api, 'chat').mockResolvedValue(page({
      may_post: false, blocked_reason: 'You are muted here until 2026-09-08T12:00:00+00:00.',
    }))
    renderChat()
    expect(await screen.findByText(/muted here until/i)).toBeInTheDocument()
  })

  it('surfaces a rejected message’s reason rather than a generic failure', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(signedIn as never)
    vi.spyOn(api, 'chat').mockResolvedValue(page({ messages: [] }))
    vi.spyOn(api, 'postChat').mockRejectedValue(
      new Error('You are sending messages too quickly. Wait a moment.'),
    )
    renderChat()
    const input = await screen.findByLabelText(/message/i)
    await userEvent.type(input, 'hello')
    await userEvent.click(screen.getByRole('button', { name: /send/i }))
    expect(await screen.findByText(/too quickly/i)).toBeInTheDocument()
  })

  it('marks a Stat Edge message as the system speaking', async () => {
    vi.spyOn(api, 'session').mockResolvedValue(signedIn as never)
    vi.spyOn(api, 'chat').mockResolvedValue(page({
      messages: [message({
        system: true, display_name: 'Stat Edge', username: 'statedge', user_id: '',
        text: 'Live projection moved 14% toward BUF.',
      })],
    }))
    renderChat()
    expect(await screen.findByText('Stat Edge')).toBeInTheDocument()
    expect(screen.getByText(/moved 14%/)).toBeInTheDocument()
  })
})

describe('Drive feed', () => {
  const play = (over: Partial<PlayOut> = {}): PlayOut => ({
    period: 2, clock: '5:12', text: 'Rush for 13 yards', team_abbr: 'BUF',
    scoring: false, start_yard_line: 25, end_yard_line: 38, yards_gained: 13,
    down: 1, distance: 10, drive_id: 'd1', drive_description: 'Touchdown', ...over,
  })

  it('groups plays into the drive they belong to', () => {
    render(<DriveFeed plays={[play(), play({ text: 'Pass for 5' })]} />)
    expect(screen.getByText(/2 plays/)).toBeInTheDocument()
    expect(screen.getByText('Touchdown')).toBeInTheDocument()
  })

  it('shows where the ball went, in words a commentator would use', () => {
    render(<DriveFeed plays={[play()]} />)
    expect(screen.getByText(/own 25 → own 38/)).toBeInTheDocument()
    expect(screen.getByText('+13')).toBeInTheDocument()
  })

  it('reads the far half of the field as the opponent’s', () => {
    render(<DriveFeed plays={[play({ start_yard_line: 60, end_yard_line: 95 })]} />)
    expect(screen.getByText(/opp 40 → opp 5/)).toBeInTheDocument()
  })

  it('still shows a play the feed gave no position for', () => {
    render(<DriveFeed plays={[play({
      start_yard_line: null, end_yard_line: null, yards_gained: null,
    })]} />)
    expect(screen.getByText('Rush for 13 yards')).toBeInTheDocument()
    expect(screen.queryByText(/own \d+ →/)).not.toBeInTheDocument()
  })

  it('marks a loss differently from a gain', () => {
    render(<DriveFeed plays={[play({ yards_gained: -4, text: 'Sacked for -4' })]} />)
    expect(screen.getByText('-4')).toBeInTheDocument()
  })
})
