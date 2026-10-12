// Minimal hash router: "#/quests/Dragon Slayer I" -> ["quests", "Dragon Slayer I"]
function currentPath(): string[] {
  const hash = window.location.hash.replace(/^#\/?/, '')
  const [page = '', ...rest] = hash.split('/')
  const param = rest.length ? decodeURIComponent(rest.join('/')) : ''
  return param ? [page, param] : [page]
}

export const route = $state({ segments: currentPath() })

window.addEventListener('hashchange', () => {
  route.segments = currentPath()
  window.scrollTo(0, 0)
})

export function href(page: string, param?: string): string {
  return param ? `#/${page}/${encodeURIComponent(param)}` : `#/${page}`
}

export function navigate(page: string, param?: string) {
  window.location.hash = href(page, param).slice(1)
}
