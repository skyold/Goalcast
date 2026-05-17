// frontend/src/lib/format.ts
export function fmtKickoff(iso: string): { day: string; time: string; date: string } {
  const d = new Date(iso);
  const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
  const day = days[d.getDay()];
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return { day, time: `${hh}:${mm}`, date: `${d.getMonth() + 1}/${d.getDate()}` };
}

export function fmtTimeAgo(iso: string | null | undefined): string {
  if (!iso) return '—';
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (diff < 1) return '刚刚';
  if (diff < 60) return `${diff} 分钟前`;
  if (diff < 60 * 24) return `${Math.floor(diff / 60)} 小时前`;
  return `${Math.floor(diff / 60 / 24)} 天前`;
}
