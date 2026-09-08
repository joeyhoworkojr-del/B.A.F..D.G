import { useRef, useState } from 'react'
import { api } from '../../api/client'
import { Avatar } from '../Avatar'
import { useSession } from '../../session/SessionProvider'

const MAX_SOURCE_BYTES = 8 * 1024 * 1024   // what we will read off disk
const OUTPUT_SIZE = 256                     // square, the size every use site needs
const QUALITY = 0.85

/**
 * Crop, resize and upload a profile photo.
 *
 * The image is centre-cropped to a square and scaled to 256px in the browser
 * before it is sent, which keeps a 6 MB phone photo from becoming a 6 MB row
 * and means the server never has to decode an arbitrary user-supplied image —
 * a large attack surface for a feature whose whole requirement is "a small
 * square picture".
 */
function toSquareJpeg(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      const side = Math.min(img.width, img.height)
      const canvas = document.createElement('canvas')
      canvas.width = canvas.height = OUTPUT_SIZE
      const ctx = canvas.getContext('2d')
      if (!ctx) { reject(new Error('This browser cannot process images.')); return }
      ctx.drawImage(
        img,
        (img.width - side) / 2, (img.height - side) / 2, side, side,
        0, 0, OUTPUT_SIZE, OUTPUT_SIZE,
      )
      resolve(canvas.toDataURL('image/jpeg', QUALITY))
    }
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('That file is not an image.')) }
    img.src = url
  })
}

export function AvatarUpload() {
  const { user, applySession } = useSession()
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  if (!user) return null

  const pick = async (file?: File | null) => {
    if (!file) return
    setError('')
    if (file.size > MAX_SOURCE_BYTES) {
      setError('That image is very large. Try one under 8 MB.')
      return
    }
    setBusy(true)
    try {
      const dataUrl = await toSquareJpeg(file)
      applySession(await api.uploadAvatar(dataUrl))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'That photo could not be uploaded.')
    } finally {
      setBusy(false)
      if (input.current) input.current.value = ''
    }
  }

  const remove = async () => {
    setBusy(true)
    setError('')
    try {
      applySession(await api.removeAvatar())
    } catch (e) {
      setError(e instanceof Error ? e.message : 'That photo could not be removed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-4">
      <Avatar user={user} size={72} />
      <div className="min-w-0">
        <input
          ref={input}
          type="file"
          accept="image/jpeg,image/png,image/gif,image/webp"
          className="sr-only"
          id="avatar-file"
          onChange={e => pick(e.target.files?.[0])}
        />
        <div className="flex flex-wrap gap-2">
          <label
            htmlFor="avatar-file"
            className="tap inline-flex cursor-pointer items-center rounded-lg border border-terminal-border bg-terminal-surface px-3 text-sm font-semibold text-zinc-300 hover:text-zinc-100"
          >
            {busy ? 'Working…' : user.avatar_url ? 'Replace photo' : 'Upload photo'}
          </label>
          {user.avatar_url && (
            <button
              type="button"
              onClick={remove}
              disabled={busy}
              className="tap inline-flex items-center rounded-lg px-3 text-sm font-semibold text-zinc-500 hover:text-signal-red disabled:opacity-60"
            >
              Remove
            </button>
          )}
        </div>
        <p className="mt-1.5 text-xs text-zinc-500">
          Cropped to a square and resized before it leaves your device. JPEG, PNG, GIF or
          WebP. Without a photo your initials are used.
        </p>
        {error && <p role="alert" className="mt-1.5 text-xs text-signal-red">{error}</p>}
      </div>
    </div>
  )
}
