import { afterEach, describe, expect, it, vi } from 'vitest'
import { authApi } from './client'

afterEach(() => vi.unstubAllGlobals())

describe('API error handling', () => {
  it('formats FastAPI validation errors without exposing submitted input', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: [
      { loc: ['body', 'email'], msg: 'Invalid email', input: 'private@example.test' },
    ] }), { status: 422 })))
    await expect(authApi.me('token')).rejects.toMatchObject({
      message: 'email: Invalid email', details: ['email: Invalid email'], status: 422,
    })
  })

  it.each(['null', '<html>Bad Gateway</html>', '{"detail":{"unexpected":true}}'])(
    'handles an unexpected error body: %s', async body => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status: 502 })))
      await expect(authApi.me('token')).rejects.toMatchObject({ message: 'Request failed (502)', status: 502 })
    },
  )
})

describe('AI event stream', () => {
  it('decodes split UTF-8 data, handles multiline events and closes on completion', async () => {
    const cancel = vi.fn()
    const encoded = new TextEncoder().encode('event: text\ndata: {"text":"你好"}\n\nevent: done\ndata: {\ndata: "quota": {}\ndata: }\n\n')
    const stream = new ReadableStream({
      start(controller) {
        for (const byte of encoded) controller.enqueue(new Uint8Array([byte]))
        // Deliberately keep the transport open after the terminal event.
      },
      cancel,
    })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(stream)))
    const onText = vi.fn()
    await expect(authApi.sendAiMessageStream('token', 'id', 'prompt', 'standard', onText)).resolves.toEqual({ quota: {} })
    expect(onText).toHaveBeenCalledWith('你好')
    expect(cancel).toHaveBeenCalledOnce()
    expect(stream.locked).toBe(false)
  })

  it('cancels the reader on provider errors', async () => {
    const cancel = vi.fn()
    const stream = new ReadableStream({
      start(controller) { controller.enqueue(new TextEncoder().encode('event: error\ndata: {"code":"provider_request_failed"}\n\n')) },
      cancel,
    })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(stream)))
    await expect(authApi.sendAiMessageStream('token', 'id', 'prompt', 'standard', vi.fn())).rejects.toMatchObject({ code: 'provider_request_failed' })
    expect(cancel).toHaveBeenCalledOnce()
    expect(stream.locked).toBe(false)
  })
})
