// frontend/src/lib/format.ts — locale-aware kickoff + relative time helpers.
// Reads the current locale at call-time from the i18n module to avoid threading
// it through every callsite. Components rerender on locale change because they
// also call useLocale() somewhere up the tree.
import { t, getLocale } from './i18n'

export function fmtKickoff(iso: string): { day: string; time: string; date: string } {
  const d = new Date(iso);
  const day = t(`weekday.${d.getDay()}`);
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return { day, time: `${hh}:${mm}`, date: `${d.getMonth() + 1}/${d.getDate()}` };
}

export function fmtTimeAgo(iso: string | null | undefined): string {
  if (!iso) return '—';
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  const locale = getLocale();
  if (diff < 1) return locale === 'en' ? 'just now' : '刚刚';
  if (diff < 60) return locale === 'en' ? `${diff} min ago` : `${diff} 分钟前`;
  if (diff < 60 * 24) return locale === 'en' ? `${Math.floor(diff / 60)}h ago` : `${Math.floor(diff / 60)} 小时前`;
  return locale === 'en' ? `${Math.floor(diff / 60 / 24)}d ago` : `${Math.floor(diff / 60 / 24)} 天前`;
}
