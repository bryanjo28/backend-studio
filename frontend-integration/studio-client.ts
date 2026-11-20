// Copy into your downloaded Vite/React frontend. No API keys required.
const BASE = (import.meta.env.VITE_STUDIO_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
export interface Config {
  title: string; aspect: '16:9' | '9:16'; resolution: '720p' | '1080p' | '1440p' | '2160p';
  fps: 24 | 30; style: 'emerald' | 'ember' | 'arctic' | 'sakura' | 'retro'; captions: boolean;
}
export interface Shot { id: string; start: number; end: number; line?: string; scene?: string; [key: string]: unknown }
export interface Story { duration: number; shots: Shot[]; [key: string]: unknown }
export interface Project { slug: string; config: Config; story: Story }
export interface Asset { path: string; url: string; size: number }
export interface Job {
  id: string; slug: string; kind: string; status: 'queued' | 'running' | 'succeeded' | 'failed';
  log: string; artifacts: string[]; error?: string; exit_code?: number;
}
async function request<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const form = body instanceof FormData;
  const response = await fetch(`${BASE}${path}`, {
    method, headers: body !== undefined && !form ? {'Content-Type': 'application/json'} : undefined,
    body: body === undefined ? undefined : form ? body : JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(typeof error?.detail === 'string' ? error.detail : JSON.stringify(error?.detail || `HTTP ${response.status}`));
  }
  return response.json();
}
const projectPath = (slug: string) => `/api/projects/${encodeURIComponent(slug)}`;
export const studio = {
  health: () => request<{status: string}>('/api/health'),
  styles: () => request<{id:string; name:string}[]>('/api/styles'),
  projects: () => request<Project[]>('/api/projects'),
  project: (slug:string) => request<Project>(projectPath(slug)),
  create: (data: Partial<Config> & {slug:string; template?:'empty'|'demo'}) => request<Project>('/api/projects','POST',data),
  config: (slug:string, data:Partial<Config>) => request<Config>(`${projectPath(slug)}/config`,'PATCH',data),
  story: (slug:string, data:Story) => request<Story>(`${projectPath(slug)}/story`,'PUT',data),
  storyline: (slug:string) => request<{text:string}>(`${projectPath(slug)}/storyline`),
  saveStoryline: (slug:string, text:string) => request<{text:string}>(`${projectPath(slug)}/storyline`,'PUT',{text}),
  assets: (slug:string) => request<Asset[]>(`${projectPath(slug)}/assets`),
  upload: (slug:string, file:File, category:'characters'|'backgrounds'|'props'|'voiceover'|'script') => {
    const form = new FormData(); form.append('file',file); form.append('category',category);
    return request<Asset>(`${projectPath(slug)}/assets`,'POST',form);
  },
  render: (slug:string, data:{kind:'sheet'|'preview'|'render'|'mix'; start?:number; end?:number; scale?:number}) => request<Job>(`${projectPath(slug)}/jobs`,'POST',data),
  job: (id:string) => request<Job>(`/api/jobs/${encodeURIComponent(id)}`),
  fileUrl: (relativeUrl:string) => `${BASE}${relativeUrl}`,
};
