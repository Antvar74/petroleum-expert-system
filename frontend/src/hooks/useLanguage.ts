import { useTranslation } from 'react-i18next';

/**
 * Shared language hook — replaces the per-module useState<Language>('es').
 * Returns the current language code and a setter that updates i18next globally.
 */
export function useLanguage() {
  const { i18n } = useTranslation();
  const language = i18n.language as 'en' | 'es';
  const setLanguage = (lng: 'en' | 'es') => i18n.changeLanguage(lng);
  return { language, setLanguage } as const;
}
