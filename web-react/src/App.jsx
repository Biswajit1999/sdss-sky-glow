import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import {
  AlertOctagon,
  AlertTriangle,
  Beaker,
  CheckCircle2,
  ChevronRight,
  Database,
  Download,
  FileText,
  GitCommit,
  ListChecks,
  MoonStar,
  Orbit,
  ShieldCheck,
  Signal,
} from 'lucide-react';

const ObservatoryHero = lazy(() => import('./ObservatoryHero.jsx'));
const panel = 'observatory-panel border border-emerald-300/15 bg-[#07130f]/85 p-5 md:p-6';

function useJson(path) {
  const [state, setState] = useState({ data: null, error: null, loading: true });

  useEffect(() => {
    let cancelled = false;
    fetch(path)
      .then((response) => {
        if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
        return response.json();
      })
      .then((data) => {
        if (!cancelled) setState({ data, error: null, loading: false });
      })
      .catch((error) => {
        if (!cancelled) setState({ data: null, error, loading: false });
      });

    return () => {
      cancelled = true;
    };
  }, [path]);

  return state;
}

function MetricCard({ metric, index }) {
  const hasUncertainty = metric.uncertainty_low != null && metric.uncertainty_high != null;

  return (
    <article className="metric-readout relative border-l border-emerald-300/20 px-4 py-5 first:border-l-0">
      <div className="mb-4 flex items-center justify-between gap-3">
        <span className="font-mono text-[0.62rem] uppercase tracking-[0.18em] text-emerald-300/70">
          channel {String(index + 1).padStart(2, '0')}
        </span>
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 shadow-[0_0_10px_#6ee7b7]" />
      </div>
      <p className="min-h-10 text-xs font-medium uppercase leading-relaxed tracking-[0.08em] text-[#9eb9ad]">
        {metric.name.replace(/_/g, ' ')}
      </p>
      <p className="mt-3 break-words font-mono text-xl font-semibold text-[#ebfff6]">
        {typeof metric.estimate === 'number' ? metric.estimate.toPrecision(4) : String(metric.estimate)}
      </p>
      <p className="mt-1 text-[0.68rem] leading-relaxed text-[#7fa092]">{metric.units}</p>
      {hasUncertainty && (
        <p className="mt-3 font-mono text-[0.68rem] text-emerald-200/80">
          95% CI [{metric.uncertainty_low.toPrecision(3)}, {metric.uncertainty_high.toPrecision(3)}]
        </p>
      )}
      <p className="mt-2 font-mono text-[0.65rem] text-[#638073]">n = {metric.sample_size}</p>
    </article>
  );
}

function SectionHeading({ icon: Icon, kicker, title, id }) {
  return (
    <div className="mb-5 flex items-center gap-3 border-b border-emerald-200/10 pb-4">
      <span className="grid h-9 w-9 place-items-center border border-emerald-300/25 bg-emerald-300/5 text-emerald-300">
        <Icon size={17} aria-hidden="true" />
      </span>
      <div>
        <p className="font-mono text-[0.6rem] uppercase tracking-[0.24em] text-emerald-300/60">{kicker}</p>
        <h2 id={id} className="text-lg font-semibold tracking-wide text-[#ecfff7]">{title}</h2>
      </div>
    </div>
  );
}

function inverseNormalCDF(p) {
  if (p <= 0 || p >= 1) return NaN;
  const a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00];
  const b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01];
  const c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00];
  const d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00];
  const pLow = 0.02425;
  const pHigh = 1 - pLow;
  let q;
  let r;

  if (p < pLow) {
    q = Math.sqrt(-2 * Math.log(p));
    return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
      / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  if (p <= pHigh) {
    q = p - 0.5;
    r = q * q;
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
      / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
  }
  q = Math.sqrt(-2 * Math.log(1 - p));
  return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
    / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
}

function ConfidenceExplorer({ metrics }) {
  const withCI = useMemo(
    () => (metrics || []).filter((metric) => metric.uncertainty_low != null && metric.uncertainty_high != null),
    [metrics],
  );
  const [selected, setSelected] = useState(null);
  const [confidence, setConfidence] = useState(95);

  useEffect(() => {
    if (!selected && withCI.length > 0) setSelected(withCI[0].name);
  }, [selected, withCI]);

  if (withCI.length === 0) return null;
  const metric = withCI.find((item) => item.name === selected) ?? withCI[0];
  const sigma = ((metric.uncertainty_high - metric.uncertainty_low) / 2) / 1.959963984540054;
  const zLevel = inverseNormalCDF(0.5 + confidence / 200);
  const low = metric.estimate - zLevel * sigma;
  const high = metric.estimate + zLevel * sigma;

  return (
    <article className={panel}>
      <SectionHeading icon={Signal} kicker="interactive check" title="Confidence-level explorer" />
      <p className="mb-5 text-xs leading-relaxed text-[#86a597]">
        This client-side approximation rescales the reported 95% bootstrap interval under a normal
        sampling assumption. It does not rerun the bootstrap or replace the computed interval.
      </p>
      <select
        className="mb-4 w-full border border-emerald-300/20 bg-[#03100b] px-3 py-2 text-sm text-[#dff8ed]"
        value={metric.name}
        onChange={(event) => setSelected(event.target.value)}
      >
        {withCI.map((item) => (
          <option key={item.name} value={item.name}>{item.name.replace(/_/g, ' ')}</option>
        ))}
      </select>
      <label className="flex items-center justify-between text-xs uppercase tracking-[0.14em] text-[#9bb5a9]">
        <span>Confidence level</span>
        <span className="font-mono text-emerald-300">{confidence.toFixed(1)}%</span>
      </label>
      <input
        type="range"
        min="50"
        max="99.9"
        step="0.1"
        value={confidence}
        onChange={(event) => setConfidence(Number(event.target.value))}
        className="mt-3 w-full accent-emerald-400"
      />
      <p className="mt-5 font-mono text-2xl font-semibold text-[#ebfff6]">
        [{low.toPrecision(4)}, {high.toPrecision(4)}]
      </p>
      <p className="mt-2 text-xs text-[#759387]">{metric.units}; n = {metric.sample_size}</p>
    </article>
  );
}

const WARNING_RULES = [
  {
    matches: (warning) => /only \d+ good baseline pixels/i.test(warning),
    title: 'Insufficient continuum baseline',
    description: 'The local continuum fit was skipped where fewer than four valid baseline pixels remained.',
    tone: 'quality',
  },
  {
    matches: (warning) => /only \d+ finite residual pixels/i.test(warning),
    title: 'Insufficient finite residuals',
    description: 'The window statistic was skipped where fewer than three finite residual samples remained.',
    tone: 'quality',
  },
  {
    matches: (warning) => /below minimum|underpowered|small sample/i.test(warning),
    title: 'Underpowered groups',
    description: 'These strata remain documented but do not reach the configured sample-size threshold.',
    tone: 'limitation',
  },
  {
    matches: (warning) => /checksum|schema|corrupt|fatal|zero[- ]tolerance/i.test(warning),
    title: 'Data-integrity failures',
    description: 'These notices indicate a failed integrity or schema requirement and require attention.',
    tone: 'failure',
  },
];

function groupWarnings(records) {
  const groups = new Map();

  records.forEach((warning) => {
    const rule = WARNING_RULES.find((candidate) => candidate.matches(warning)) ?? {
      title: 'Other recorded notices',
      description: 'Additional pipeline notices retained for complete auditability.',
      tone: 'limitation',
    };
    if (!groups.has(rule.title)) groups.set(rule.title, { ...rule, entries: [] });
    groups.get(rule.title).entries.push(warning);
  });

  return [...groups.values()];
}

function WarningLedger({ state }) {
  const records = useMemo(() => (Array.isArray(state.data) ? state.data : []), [state.data]);
  const groups = useMemo(() => groupWarnings(records), [records]);

  if (state.loading) return <p className="text-sm text-[#8dab9d]">Reading warning ledger…</p>;
  if (state.error) {
    return (
      <div className="border border-red-400/30 bg-red-950/30 p-4 text-sm text-red-200">
        warnings.json could not be loaded: {String(state.error)}
      </div>
    );
  }
  if (records.length === 0) {
    return (
      <div className="flex items-center gap-2 border border-emerald-300/20 bg-emerald-300/5 p-4 text-sm text-emerald-100">
        <CheckCircle2 size={17} aria-hidden="true" />
        No warnings recorded in results/warnings.json.
      </div>
    );
  }

  const failureCount = groups
    .filter((group) => group.tone === 'failure')
    .reduce((total, group) => total + group.entries.length, 0);

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <p className="max-w-3xl text-sm leading-relaxed text-[#9cb8ab]">
          <strong className="text-[#e5fff3]">{records.length} analysis notices</strong> are grouped
          by cause. Expected quality-control exclusions are separated from integrity failures.
        </p>
        <span className={`border px-3 py-1 font-mono text-xs ${failureCount > 0 ? 'border-red-400/40 bg-red-950/40 text-red-200' : 'border-emerald-300/25 bg-emerald-300/5 text-emerald-200'}`}>
          {failureCount > 0 ? `${failureCount} integrity failures` : '0 integrity failures'}
        </span>
      </div>
      <div className="grid gap-px overflow-hidden border border-emerald-200/10 bg-emerald-200/10 md:grid-cols-2">
        {groups.map((group) => (
          <div key={group.title} className={`warning-${group.tone} bg-[#07130f] p-5`}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-semibold text-[#e8fff5]">{group.title}</p>
                <p className="mt-2 text-xs leading-relaxed text-[#829f92]">{group.description}</p>
              </div>
              <span className="grid h-9 min-w-9 place-items-center border border-emerald-300/20 bg-emerald-300/5 font-mono text-sm text-emerald-200">
                {group.entries.length}
              </span>
            </div>
          </div>
        ))}
      </div>
      <details className="raw-ledger mt-4 border border-emerald-300/15 bg-[#04100c] p-4">
        <summary className="cursor-pointer font-mono text-xs uppercase tracking-[0.13em] text-emerald-200">
          Show all {records.length} raw entries from warnings.json
        </summary>
        <ol className="mt-4 max-h-80 space-y-2 overflow-auto border-t border-emerald-200/10 pt-4 font-mono text-[0.68rem] leading-relaxed text-[#86a396]">
          {records.map((warning, index) => <li key={`${index}-${warning}`}>{warning}</li>)}
        </ol>
      </details>
    </div>
  );
}

function FigureCatalogue({ figures }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-12">
      {figures.map((figure, index) => {
        const span = index < 2 ? 'xl:col-span-6' : 'xl:col-span-4';
        return (
          <figure key={figure.id} className={`figure-plate group border border-emerald-200/12 bg-[#07120e] p-3 ${span}`}>
            <div className="overflow-hidden bg-white">
              <img
                src={`./figures/${figure.id}.svg`}
                alt={figure.label}
                className="w-full transition duration-500 group-hover:scale-[1.012]"
                onError={(event) => { event.currentTarget.style.display = 'none'; }}
              />
            </div>
            <figcaption className="flex items-center justify-between gap-3 px-1 pb-1 pt-3">
              <span className="text-sm text-[#c6ded3]">{figure.label}</span>
              <span className="font-mono text-[0.58rem] uppercase tracking-[0.16em] text-emerald-300/65">
                plate {String(index + 1).padStart(2, '0')}
              </span>
            </figcaption>
          </figure>
        );
      })}
    </div>
  );
}

export default function App() {
  const project = useJson('./project.json');
  const summary = useJson('./results/summary.json');
  const warnings = useJson('./results/warnings.json');
  const benchmarks = useJson('./results/benchmarks.json');

  if (project.loading) {
    return <main className="grid min-h-screen place-items-center bg-[#020806] text-emerald-200">Opening observing log…</main>;
  }
  if (project.error || !project.data) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#020806] px-6 text-red-200">
        Could not load project.json: {String(project.error)}
      </main>
    );
  }

  const p = project.data;
  const isDemo = summary.data?.data_kind === 'synthetic_smoke_test' || summary.data?.data_kind === 'synthetic_demo';

  return (
    <main className="night-sky-page min-h-screen bg-[#020806] text-[#d8eee4]">
      <header className="night-hero relative overflow-hidden border-b border-emerald-300/15">
        <div className="star-field" aria-hidden="true" />
        <div className="relative mx-auto grid min-h-[42rem] max-w-[90rem] grid-cols-1 px-5 md:px-8 lg:grid-cols-[5rem_1fr_0.9fr]">
          <aside className="hidden border-x border-emerald-300/10 py-10 lg:flex lg:flex-col lg:items-center lg:justify-between">
            <span className="font-mono text-[0.6rem] uppercase tracking-[0.3em] text-emerald-300/60 [writing-mode:vertical-rl]">released-product audit</span>
            <span className="font-mono text-3xl text-emerald-300">06</span>
          </aside>
          <div className="flex flex-col justify-center py-12 lg:px-12">
            <div className="mb-7 flex items-center gap-3 font-mono text-[0.65rem] uppercase tracking-[0.24em] text-emerald-300/75">
              <MoonStar size={16} />
              {p.category}
            </div>
            <h1 className="hero-title max-w-4xl text-4xl font-semibold uppercase leading-[0.95] tracking-[-0.045em] text-[#edfff7] md:text-6xl xl:text-7xl">
              {p.title}
            </h1>
            <p className="mt-7 max-w-3xl border-l border-emerald-300/35 pl-5 text-base leading-relaxed text-[#a4c1b4] md:text-lg">
              {p.question}
            </p>
            <div className="mt-8 flex flex-wrap gap-2 font-mono text-[0.65rem] uppercase tracking-[0.1em]">
              <span className="status-tag">{p.status}</span>
              <span className="status-tag">priority {p.priority}/10</span>
              <span className="status-tag">{p.dataMode}</span>
              {summary.data && (
                <span className={`status-tag ${isDemo ? 'status-demo' : 'status-real'}`}>
                  {isDemo ? 'synthetic demo results' : 'real data results'}
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center pb-10 lg:pb-0">
            <Suspense fallback={<div className="h-[26rem] w-full animate-pulse border border-emerald-300/10 bg-emerald-300/[0.025]" />}>
              <ObservatoryHero />
            </Suspense>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[90rem] px-5 py-10 md:px-8 md:py-14">
        {isDemo && (
          <div className="mb-8 flex items-start gap-3 border border-amber-300/25 bg-amber-300/5 p-4 text-sm text-amber-100">
            <AlertTriangle size={18} className="mt-0.5 shrink-0" aria-hidden="true" />
            The displayed metrics and figures are clearly labelled synthetic demo outputs, not SDSS observations.
            Real-data outputs replace them after the archive pipeline runs.
          </div>
        )}

        <section aria-labelledby="metrics-title" className="border border-emerald-200/12 bg-[#06110d]">
          <div className="flex flex-wrap items-end justify-between gap-4 border-b border-emerald-200/10 px-5 py-4">
            <div>
              <p className="font-mono text-[0.6rem] uppercase tracking-[0.24em] text-emerald-300/60">spectral signal band</p>
              <h2 id="metrics-title" className="mt-1 text-lg font-semibold text-[#effff8]">Measured outputs</h2>
            </div>
            <p className="font-mono text-[0.65rem] text-[#6e8d7f]">live: results/summary.json</p>
          </div>
          <div className="grid md:grid-cols-2 xl:grid-cols-5">
            {summary.data?.metrics?.map((metric, index) => (
              <MetricCard key={metric.name} metric={metric} index={index} />
            ))}
            {!summary.data && (
              <article className="p-5">
                <p className="font-mono text-lg text-[#effff8]">NO RESULTS YET</p>
                <p className="mt-2 text-xs text-[#759387]">Run scripts/run_analysis.py first.</p>
              </article>
            )}
          </div>
        </section>

        <section className="mt-6 grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
          <ConfidenceExplorer metrics={summary.data?.metrics} />
          <article className={panel}>
            <SectionHeading icon={ShieldCheck} kicker="scope and traceability" title="Provenance boundary" />
            <p className="text-sm leading-relaxed text-[#9ab5a8]">{p.novelty}</p>
            <div className="mt-5 flex items-start gap-3 border border-amber-300/20 bg-amber-300/5 p-4 text-sm text-amber-100">
              <AlertTriangle size={17} className="mt-0.5 shrink-0" aria-hidden="true" />
              Results are public-ready only after validation and provenance checks pass.
            </div>
            {summary.data?.provenance && (
              <dl className="mt-5 grid gap-3 text-xs text-[#9ab5a8] sm:grid-cols-3">
                <div className="border border-emerald-200/10 p-3"><GitCommit size={14} /><dt className="mt-2 text-[#638174]">git commit</dt><dd className="mt-1 font-mono text-[#d9eee5]">{summary.data.provenance.git_commit}</dd></div>
                <div className="border border-emerald-200/10 p-3"><FileText size={14} /><dt className="mt-2 text-[#638174]">config sha256</dt><dd className="mt-1 truncate font-mono text-[#d9eee5]">{summary.data.provenance.config_sha256 ?? 'n/a'}</dd></div>
                <div className="border border-emerald-200/10 p-3"><Beaker size={14} /><dt className="mt-2 text-[#638174]">package</dt><dd className="mt-1 font-mono text-[#d9eee5]">{summary.data.provenance.package_version}</dd></div>
              </dl>
            )}
          </article>
        </section>

        <section className="mt-6 grid gap-6 lg:grid-cols-[0.7fr_1.3fr]">
          <article className={panel}>
            <SectionHeading icon={ListChecks} kicker="acceptance gates" title="Validation contract" />
            <ol className="space-y-4 text-sm text-[#a1bcae]">
              {p.validationContract.map((item, index) => (
                <li key={item} className="flex gap-3">
                  <span className="font-mono text-emerald-300">{String(index + 1).padStart(2, '0')}</span>
                  <span>{item}</span>
                </li>
              ))}
            </ol>
          </article>
          <article className={panel}>
            <SectionHeading icon={Orbit} kicker="publication output" title="Figure catalogue" id="figures-title" />
            <FigureCatalogue figures={p.figures} />
          </article>
        </section>

        <section className={`mt-6 ${panel}`}>
          <SectionHeading icon={AlertTriangle} kicker="transparent reporting" title="Warnings and exclusions" />
          <WarningLedger state={warnings} />
        </section>

        <section className="mt-6 grid gap-6 xl:grid-cols-2">
          <article className={panel}>
            <SectionHeading icon={Signal} kicker="residual audit" title="Methodology" />
            <p className="text-sm leading-7 text-[#9bb7aa]">{p.methodology}</p>
          </article>
          <article className={panel}>
            <SectionHeading icon={AlertOctagon} kicker="interpretive boundary" title="Assumptions and limitations" />
            <div className="grid gap-7 md:grid-cols-2">
              <div>
                <p className="mb-4 font-mono text-[0.62rem] uppercase tracking-[0.2em] text-emerald-300">Assumptions</p>
                <ul className="space-y-4 text-xs leading-relaxed text-[#92ae9f]">
                  {p.assumptions.map((item) => <li key={item} className="border-l border-emerald-300/30 pl-3">{item}</li>)}
                </ul>
              </div>
              <div>
                <p className="mb-4 font-mono text-[0.62rem] uppercase tracking-[0.2em] text-emerald-300">Limitations</p>
                <ul className="space-y-4 text-xs leading-relaxed text-[#92ae9f]">
                  {p.limitations.map((item) => <li key={item} className="border-l border-emerald-300/30 pl-3">{item}</li>)}
                </ul>
              </div>
            </div>
          </article>
        </section>

        <footer className="mt-6 grid gap-px border border-emerald-200/10 bg-emerald-200/10 md:grid-cols-2">
          <article className="bg-[#05100c] p-6">
            <SectionHeading icon={Download} kicker="machine-readable" title="Downloads and manifest" />
            <div className="grid gap-2 text-xs sm:grid-cols-2">
              <a className="download-row" href="./manifest.csv" download><span>data/manifest.csv</span><ChevronRight size={14} /></a>
              <a className="download-row" href="./results/summary.json" download><span>results/summary.json</span><ChevronRight size={14} /></a>
              <a className="download-row" href="./results/warnings.json" download><span>results/warnings.json</span><ChevronRight size={14} /></a>
              {benchmarks.data && <a className="download-row" href="./results/benchmarks.json" download><span>results/benchmarks.json</span><ChevronRight size={14} /></a>}
            </div>
            <p className="mt-4 text-[0.68rem] leading-relaxed text-[#69877a]">
              The manifest records product ID, source, retrieval time, checksum, file size,
              selection reason, and archive terms for every spectrum used.
            </p>
          </article>
          <article className="bg-[#05100c] p-6">
            <SectionHeading icon={Database} kicker="reuse" title="Citation and licence" />
            <p className="text-sm text-[#a1bbaf]">Author: {p.citation.author}</p>
            <p className="mt-2 text-sm text-[#a1bbaf]">Licence: {p.citation.license}</p>
            <a className="mt-5 inline-flex items-center gap-2 font-mono text-xs uppercase tracking-[0.1em] text-emerald-300 hover:text-emerald-200" href={p.citation.repository}>
              Repository record <span aria-hidden="true">↗</span>
            </a>
          </article>
        </footer>
      </div>
    </main>
  );
}
