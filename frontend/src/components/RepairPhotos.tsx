// The contractor's "after" photos on a repair ticket, as small pictures that open full size. Used on the contractor's page and in the admin's ticket box,
// so the authority can look at the work before it verifies it.

const apiBaseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export const photoUrl = (url: string) => (url.startsWith("http") ? url : `${apiBaseUrl}${url}`);

export function RepairPhotos({ urls, label = "Repair photo" }: { urls: string[]; label?: string }) {
  if (urls.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {urls.map((url) => (
        <a key={url} href={photoUrl(url)} target="_blank" rel="noreferrer">
          <img src={photoUrl(url)} alt={label} className="h-24 w-32 rounded-xl object-cover" />
        </a>
      ))}
    </div>
  );
}
