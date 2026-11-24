import { BarList, Columns, StatTile } from '../../components/charts'
import { Alert, Badge, Card, CardHeader, ErrorState, Loading, PageHeader } from '../../components/ui'
import { useApi } from '../../hooks/useApi'
import { useI18n } from '../../i18n'
import { fmtDateTime } from '../../lib/format'

export default function Analytics() {
  const { t, lang } = useI18n()
  const ov = useApi('/analytics/overview/')
  const ref = useApi('/analytics/referrals/')
  const prog = useApi('/analytics/case-progress/')
  if (ov.loading || ref.loading || prog.loading) return <Loading />
  const err = ov.error || ref.error || prog.error
  if (err) return <ErrorState error={err} onRetry={() => { ov.reload(); ref.reload(); prog.reload() }} />
  const k = ov.data.min_cell_size
  const o = ov.data
  const pct = (c) => c
  return (
    <>
      <PageHeader title={t('analytics.title')} subtitle={t('analytics.subtitle', { k })} />
      <div className="mb-6"><Alert tone="info" title={t('analytics.privacyTitle')}>{t('analytics.privacy', { k })}</Alert></div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label={t('analytics.totalCases')} cell={o.totals.cases} minCell={k} />
        <StatTile label={t('analytics.totalReferrals')} cell={o.totals.referrals} minCell={k} />
        <StatTile label={t('analytics.ackRate')} cell={pct(o.rates.referral_acknowledgement_rate)} suffix="%" minCell={k} />
        <StatTile label={t('analytics.avgAck')} cell={o.avg_acknowledgement_hours} suffix=" h" minCell={k} hint={t('analytics.avgAckHint')} />
        <StatTile label={t('analytics.completionRate')} cell={o.rates.referral_completion_rate} suffix="%" minCell={k} />
        <StatTile label={t('analytics.pendingAck')} cell={o.totals.referrals_pending_acknowledgement} minCell={k} />
        <StatTile label={t('analytics.followUpRate')} cell={o.rates.follow_up_completion_rate} suffix="%" minCell={k} />
        <StatTile label={t('analytics.assistanceRate')} cell={o.rates.assistance_response_rate} suffix="%" minCell={k} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card><CardHeader title={t('analytics.byCategory')} />
          <div className="p-5"><BarList minCell={k} rows={o.cases_by_category.map((r) => ({ ...r, label: t(`incident.${r.key}`) }))} /></div></Card>
        <Card><CardHeader title={t('analytics.byRegion')} subtitle={t('analytics.byRegionHint')} />
          <div className="p-5"><BarList minCell={k} rows={o.cases_by_region.map((r) => ({ ...r, label: t(`region.${r.key}`) }))} /></div></Card>
        <Card><CardHeader title={t('analytics.referralsByCategory')} />
          <div className="p-5"><BarList minCell={k} rows={ref.data.by_category.map((r) => ({ key: r.key, label: t(`referralCategory.${r.key}`), ...r.total }))} /></div></Card>
        <Card><CardHeader title={t('analytics.completionByCategory')} />
          <div className="p-5"><BarList minCell={k} valueSuffix="%" rows={ref.data.by_category.map((r) => ({ key: r.key, label: t(`referralCategory.${r.key}`), ...r.completion_rate, value: r.completion_rate.value ?? 0, suppressed: r.completion_rate.suppressed && r.total.value !== 0 }))} /></div></Card>
        <Card><CardHeader title={t('analytics.byStage')} subtitle={t('analytics.byStageHint')} />
          <div className="p-5"><BarList minCell={k} rows={prog.data.by_stage.map((r) => ({ ...r, label: t(`stage.${r.key}`) }))} /></div></Card>
        <Card><CardHeader title={t('analytics.referralStatus')} />
          <div className="p-5"><BarList minCell={k} rows={ref.data.by_status.map((r) => ({ ...r, label: t(`referralStatus.${r.key}`) }))} /></div></Card>
        <Card><CardHeader title={t('analytics.monthly')} subtitle={t('analytics.monthlyHint')} />
          <div className="p-5 pt-10"><Columns minCell={k} rows={prog.data.monthly_registrations} /></div></Card>
        <Card><CardHeader title={t('analytics.gaps')} subtitle={t('analytics.gapsHint')} />
          <div className="space-y-3 p-5">
            <p className="text-sm text-ink">{t('analytics.stale')}: <strong>{ref.data.unacknowledged_over_7_days.suppressed ? t('analytics.suppressed', { k }) : ref.data.unacknowledged_over_7_days.value}</strong></p>
            {ref.data.service_gaps.length === 0 ? <p className="text-sm text-muted">{t('analytics.noGaps')}</p> : ref.data.service_gaps.map((g) => (
              <div key={g.category} className="rounded-lg border border-line p-3">
                <p className="font-semibold text-navy">{t(`referralCategory.${g.category}`)}</p>
                <div className="mt-1 flex flex-wrap gap-1.5">{g.reasons.map((r) => <Badge key={r} tone="warn">{t(`analytics.gap.${r}`)}</Badge>)}</div>
              </div>
            ))}
            <p className="pt-2 text-sm text-ink">{t('analytics.court')}: {t('analytics.inCourt')} <strong>{prog.data.court.cases_in_court_stages.suppressed ? t('analytics.suppressed', { k }) : prog.data.court.cases_in_court_stages.value}</strong> · {t('analytics.concluded')} <strong>{prog.data.court.cases_concluded.suppressed ? t('analytics.suppressed', { k }) : prog.data.court.cases_concluded.value}</strong></p>
          </div></Card>
      </div>
      <p className="mt-6 text-xs text-muted">{t('analytics.generated', { at: fmtDateTime(o.generated_at, lang) })}</p>
    </>
  )
}
