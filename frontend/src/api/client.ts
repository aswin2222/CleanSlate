/** Frontend HTTP API client managing token authentication and requests. */
const rawBaseUrl = ((import.meta as any).env?.VITE_API_BASE_URL as string) || '';
export const BASE_URL = rawBaseUrl.replace(/\/+$/, '');

export function getApiUrl(endpoint: string): string {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return BASE_URL ? `${BASE_URL}${cleanEndpoint}` : cleanEndpoint;
}

export function getAuthToken(): string | null {
  return localStorage.getItem('titan_token') || localStorage.getItem('cleanslate_token');
}

export function setAuthToken(token: string): void {
  localStorage.setItem('titan_token', token);
  localStorage.setItem('cleanslate_token', token);
}

export function clearAuthToken(): void {
  localStorage.removeItem('titan_token');
  localStorage.removeItem('cleanslate_token');
}

export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const url = getApiUrl(endpoint);
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    if (!endpoint.includes('/auth/login')) {
      clearAuthToken();
      if (!window.location.pathname.includes('/login') && window.location.pathname !== '/') {
        window.location.href = '/login';
      }
    }
    throw new Error('Invalid email or password');
  }

  if (!response.ok) {
    let errorDetail = 'API request failed';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail?.message || errJson.detail || JSON.stringify(errJson);
    } catch {
      errorDetail = await response.text();
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export async function downloadFile(endpoint: string, fallbackFilename?: string): Promise<void> {
  const token = getAuthToken();
  const headers = new Headers();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const fetchUrl = getApiUrl(endpoint);
  const response = await fetch(fetchUrl, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    let errorDetail = 'Download failed';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail?.message || errJson.detail || JSON.stringify(errJson);
    } catch {
      errorDetail = await response.text();
    }
    throw new Error(errorDetail);
  }

  let filename = fallbackFilename || 'cleaned_dataset';
  const disposition = response.headers.get('Content-Disposition');
  if (disposition && disposition.includes('filename=')) {
    const match = disposition.match(/filename=["']?([^"';]+)["']?/);
    if (match && match[1]) {
      filename = match[1];
    }
  }

  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(downloadUrl);
  document.body.removeChild(a);
}

