// MSW wiring for the browser: every request to API_URL goes through handleMock().
// Unknown routes fall through to the real network.
import { setupWorker } from 'msw/browser'
import { http, HttpResponse, passthrough } from 'msw'
import { API_URL } from '@/config'
import { handleMock } from './mockApi'

// Documents of the mock projects (SVG, DXF, PDF, CSV), served as real files by Vite.
const FILE_URLS = import.meta.glob('./data/documente/*/*', { query: '?url', import: 'default', eager: true }) as Record<string, string>

const handler = http.all(`${API_URL}/*`, async ({ request }) => {
  const url = new URL(request.url)
  const body = ['POST', 'PATCH', 'PUT'].includes(request.method)
    ? ((await request.json().catch(() => undefined)) as Record<string, unknown> | undefined)
    : undefined
  const userId = request.headers.get('X-User-Id') ?? ''
  const res = handleMock(request.method, url.pathname + url.search, body, userId)
  if (!res) return passthrough()
  if (res.file) {
    const href = FILE_URLS[`./data/documente/${res.file.key}`]
    if (!href) return HttpResponse.json({ detail: 'Documentul nu există.' }, { status: 404 })
    const blob = await (await fetch(href)).blob()
    return new HttpResponse(blob, { headers: { 'Content-Type': res.file.contentType } })
  }
  return HttpResponse.json(res.body as never, { status: res.status })
})

export const worker = setupWorker(handler)
