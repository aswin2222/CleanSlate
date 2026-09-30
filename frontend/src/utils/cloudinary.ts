/**
 * Cloudinary Direct Upload Utility
 * Uses Cloud Name: bgrvz383
 * Upload Preset: TITAN-project
 */

export const CLOUDINARY_CONFIG = {
  cloudName: 'bgrvz383',
  uploadPreset: 'TITAN-project',
  uploadUrl: 'https://api.cloudinary.com/v1_1/bgrvz383/raw/upload',
};

export interface CloudinaryUploadResponse {
  asset_id: string;
  public_id: string;
  version: number;
  format?: string;
  resource_type: string;
  created_at: string;
  bytes: number;
  type: string;
  url: string;
  secure_url: string;
  original_filename?: string;
}

/**
 * Uploads a file (CSV, JSON, XLSX, Parquet, etc.) directly to Cloudinary
 */
export async function uploadToCloudinary(
  file: File,
  onProgress?: (percent: number) => void
): Promise<CloudinaryUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('upload_preset', CLOUDINARY_CONFIG.uploadPreset);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', CLOUDINARY_CONFIG.uploadUrl);

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          const percent = Math.round((e.loaded / e.total) * 100);
          onProgress(percent);
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const res = JSON.parse(xhr.responseText) as CloudinaryUploadResponse;
          resolve(res);
        } catch (e) {
          reject(new Error('Failed to parse Cloudinary response'));
        }
      } else {
        try {
          const errData = JSON.parse(xhr.responseText);
          reject(new Error(errData.error?.message || `Cloudinary upload failed (${xhr.status})`));
        } catch {
          reject(new Error(`Cloudinary upload failed with status ${xhr.status}`));
        }
      }
    };

    xhr.onerror = () => {
      reject(new Error('Network error while uploading to Cloudinary'));
    };

    xhr.send(formData);
  });
}
