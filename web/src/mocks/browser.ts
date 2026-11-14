// MSW wiring for the browser: every request to API_URL goes through handleMock().
// Unknown routes fall through to the real network.
import { setupWorker } from 'msw/browser'
import { http, HttpResponse, passthrough } from 'msw'
import { API_URL } from '@/config'
import { handleMock } from './mockApi'

const handler = http.all(`${API_URL}/*`, async ({ request }) => {
  const url = new URL(request.url)
  const body = ['POST', 'PATCH', 'PUT'].includes(request.method)
    ? ((await request.json().catch(() => undefined)) as Record<string, unknown> | undefined)
    : undefined
  const userId = request.headers.get('X-User-Id') ?? ''
  const res = handleMock(request.method, url.pathname + url.search, body, userId)
  if (!res) return passthrough()
  return HttpResponse.json(res.body as never, { status: res.status })
})

export const worker = setupWorker(handler)
