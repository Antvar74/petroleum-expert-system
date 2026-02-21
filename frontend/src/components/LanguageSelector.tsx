import { useLanguage } from '../hooks/useLanguage';

const LANGS = ['en', 'es'] as const;

const LanguageSelector: React.FC = () => {
  const { language, setLanguage } = useLanguage();

  return (
    <div className="flex items-center bg-white/5 rounded-lg overflow-hidden border border-white/10">
      {LANGS.map((lng) => (
        <button
          key={lng}
          onClick={() => setLanguage(lng)}
          className={`px-2.5 py-1 text-xs font-bold transition-all ${
            language === lng
              ? 'bg-industrial-600 text-white'
              : 'text-white/40 hover:text-white/70'
          }`}
        >
          {lng.toUpperCase()}
        </button>
      ))}
    </div>
  );
};

export default LanguageSelector;
