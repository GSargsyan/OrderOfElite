import React, { useState, useEffect, useContext, useCallback } from 'react'
import { request } from 'modules/Base'
import { UserPreviewCtx } from 'modules/Dashboard'

const STATUS_LABELS = {
    'pending_signature': 'AWAITING SIGNATURE',
    'active': 'ACTIVE',
    'fulfilled': 'FULFILLED',
    'breached': 'BREACHED',
    'declined': 'DECLINED',
    'withdrawn': 'WITHDRAWN',
    'annulled': 'ANNULLED',
    'expired': 'EXPIRED',
}

const CLAUSE_STATUS_LABELS = {
    'waiting_trigger': 'PENDING',
    'armed': 'IN EFFECT',
    'fulfilled': 'FULFILLED',
    'breached': 'BREACHED',
    'lapsed': 'LAPSED',
}

/* Two-step confirmation button (same pattern as leaving the Citadel). */
function ConfirmButton({ className, label, confirmLabel, disabled, onConfirm }) {
    const [confirming, setConfirming] = useState(false)

    useEffect(() => {
        if (!confirming) return
        const timer = setTimeout(() => setConfirming(false), 4000)
        return () => clearTimeout(timer)
    }, [confirming])

    const handleClick = () => {
        if (!confirming) {
            setConfirming(true)
            return
        }
        setConfirming(false)
        onConfirm()
    }

    return (
        <button
            className={`${className} ${confirming ? 'confirming' : ''}`}
            disabled={disabled}
            onClick={handleClick}
        >
            {confirming ? confirmLabel : label}
        </button>
    )
}

/* Blurred placeholder shown behind the lock for non-members. */
function LockedSeals() {
    return (
        <div className="seals-locked-wrapper">
            <div className="seals-locked-backdrop">
                <div className="seals-section-title">CREATE A SEAL</div>
                <p className="seals-note">
                    Seals are binding written contracts between two players. Once both
                    parties sign, the game automatically tracks and enforces the agreed
                    terms — breach marks the offending player as Persona Non Grata and
                    permanently records the breach.
                </p>
                <div className="seal-card">
                    <div className="seal-card-parties">SIGNED — TWO PARTIES BOUND</div>
                    <div className="seal-card-text">
                        Clause I — Upon the signing of this Seal, the second party
                        shall travel to Moscow within 7 days.
                    </div>
                </div>
                <div className="seal-card">
                    <div className="seal-card-parties">AWAITING SIGNATURE</div>
                    <div className="seal-card-text">
                        Clause I — Should the first party leave the Citadel, they
                        shall not set foot in Rome for 14 days.
                    </div>
                </div>
            </div>
            <div className="seals-locked-overlay">
                <div className="seals-locked-icon">🔒</div>
                <div className="seals-locked-title">RESERVED FOR MEMBERS</div>
                <div className="seals-locked-text">
                    Seals are available to Premium members. Membership can be
                    purchased in the Premium section.
                </div>
            </div>
        </div>
    )
}

function SealCard({ seal, username, onAction, busy }) {
    const statusClass = `seal-status-${seal.status}`

    const annulLabel = () => {
        if (!seal.annul_requested_by) return 'REQUEST ANNULMENT'
        if (seal.annul_requested_by === username) return 'ANNULMENT REQUESTED'
        return 'CONSENT TO ANNULMENT'
    }

    return (
        <div className="seal-card">
            <div className="seal-card-header">
                <span className="seal-card-parties">
                    {seal.creator.toUpperCase()} ⇌ {seal.counterparty.toUpperCase()}
                </span>
                <span className={`seal-card-status ${statusClass}`}>
                    {STATUS_LABELS[seal.status] || seal.status.toUpperCase()}
                </span>
            </div>

            <div className="seal-card-text">
                <p>{seal.raw_text}</p>
            </div>

            <div className="seal-card-terms">
                <span>DEADLINE — {seal.deadline_days} DAYS</span>
                <span>ON BREACH — PERSONA NON GRATA, {seal.penalty_png_days} DAYS</span>
            </div>

            {seal.status === 'active' && seal.clauses.length > 0 && (
                <div className="seal-card-clauses">
                    {seal.clauses.map((clause, i) => (
                        <span key={i} className={`seal-clause-chip seal-clause-${clause.status}`}>
                            {['I', 'II', 'III'][i]} · {clause.obligor.toUpperCase()} · {CLAUSE_STATUS_LABELS[clause.status]}
                        </span>
                    ))}
                </div>
            )}

            <div className="seal-card-actions">
                {seal.status === 'pending_signature' && !seal.is_creator && (
                    <>
                        <ConfirmButton
                            className="btn-seal-primary"
                            label="SIGN"
                            confirmLabel="SIGNING BINDS YOU — CONFIRM"
                            disabled={busy}
                            onConfirm={() => onAction('sign', seal.id)}
                        />
                        <button
                            className="btn-seal-secondary"
                            disabled={busy}
                            onClick={() => onAction('decline', seal.id)}
                        >
                            DECLINE
                        </button>
                    </>
                )}

                {seal.status === 'pending_signature' && seal.is_creator && (
                    <button
                        className="btn-seal-secondary"
                        disabled={busy}
                        onClick={() => onAction('withdraw', seal.id)}
                    >
                        WITHDRAW
                    </button>
                )}

                {seal.status === 'active' && (
                    <ConfirmButton
                        className="btn-seal-secondary"
                        label={annulLabel()}
                        confirmLabel="CONFIRM ANNULMENT REQUEST"
                        disabled={busy || seal.annul_requested_by === username}
                        onConfirm={() => onAction('annul', seal.id)}
                    />
                )}
            </div>

            {seal.status === 'pending_signature' && !seal.is_creator && (
                <div className="seals-note seals-sign-warning">
                    If you sign this Seal you are bound to fulfill it. Failure
                    renders you persona non grata and permanently marks your record.
                </div>
            )}
        </div>
    )
}

function SealsTab() {
    const { userPreviewData, updateUserPreviewData } = useContext(UserPreviewCtx)

    const [tabData, setTabData] = useState(null)
    const [counterparty, setCounterparty] = useState('')
    const [rawText, setRawText] = useState('')
    const [deadlineDays, setDeadlineDays] = useState(7)
    const [penaltyDays, setPenaltyDays] = useState(7)
    const [preview, setPreview] = useState(null)
    const [formError, setFormError] = useState(null)
    const [busy, setBusy] = useState(false)

    const isPremium = userPreviewData?.is_premium

    const loadTabData = useCallback(() => {
        request({ url: 'seals/get_tab_data', method: 'POST' })
            .then(res => setTabData(res.data))
            .catch(err => console.error('SealsTab load error:', err))
    }, [])

    useEffect(() => {
        if (isPremium) loadTabData()
    }, [isPremium, loadTabData])

    if (!isPremium) {
        return <LockedSeals />
    }

    if (!tabData) {
        return <div className="loading-text">LOADING...</div>
    }

    const handleCompile = () => {
        if (busy) return
        setFormError(null)
        setBusy(true)

        request({
            url: 'seals/compile',
            method: 'POST',
            data: {
                counterparty: counterparty.trim(),
                raw_text: rawText,
                deadline_days: deadlineDays,
                penalty_png_days: penaltyDays,
            },
        })
            .then(res => setPreview(res.data))
            .catch(err => {
                setFormError(err.response?.data?.message
                    || 'The terms could not be bound.')
            })
            .finally(() => setBusy(false))
    }

    const handleAction = (action, sealId) => {
        if (busy) return
        setBusy(true)

        request({
            url: `seals/${action}`,
            method: 'POST',
            data: { seal_id: sealId },
        })
            .then(res => {
                if (res.data.message) alert(res.data.message)
                if (action === 'send') {
                    setPreview(null)
                    setCounterparty('')
                    setRawText('')
                }
                if (action === 'discard_draft') setPreview(null)
                loadTabData()
                updateUserPreviewData()
            })
            .catch(err => {
                alert(err.response?.data?.message || 'The action could not be completed.')
                loadTabData()
            })
            .finally(() => setBusy(false))
    }

    return (
        <div className="seals-tab">
            {/* ── Create ── */}
            <div className="seals-section">
                <div className="seals-section-title">CREATE A SEAL</div>

                {preview ? (
                    <div className="seal-preview-panel">
                        <div className="seals-note">
                            The Seal below is what {preview.counterparty} will be
                            presented with — your written terms, exactly as stated.
                        </div>
                        <div className="seal-card">
                            <div className="seal-card-parties">
                                {userPreviewData.username.toUpperCase()} ⇌ {preview.counterparty.toUpperCase()}
                            </div>
                            <div className="seal-card-text">
                                <p>{preview.raw_text}</p>
                            </div>
                            <div className="seal-card-terms">
                                <span>DEADLINE — {preview.deadline_days} DAYS</span>
                                <span>ON BREACH — PERSONA NON GRATA, {preview.penalty_png_days} DAYS</span>
                            </div>
                        </div>
                        <div className="seal-reading">
                            <div className="seals-section-title">READING OF THE TERMS</div>
                            {preview.rendered_text.split('\n').map((line, i) => (
                                <p key={i}>{line}</p>
                            ))}
                            <div className="seals-note" style={{ marginTop: '8px', marginBottom: 0 }}>
                                Confirm this reading matches your intent — it is how the
                                system will enforce the Seal. Only you can see this; the
                                other party sees only your written terms above.
                            </div>
                        </div>
                        <div className="seal-card-actions">
                            <button
                                className="btn-seal-primary"
                                disabled={busy}
                                onClick={() => handleAction('send', preview.seal_id)}
                            >
                                SEND FOR SIGNATURE
                            </button>
                            <button
                                className="btn-seal-secondary"
                                disabled={busy}
                                onClick={() => handleAction('discard_draft', preview.seal_id)}
                            >
                                DISCARD
                            </button>
                        </div>
                    </div>
                ) : (
                    <>
                        <div className="seals-informal-desc">
                            <p>
                                <strong>What are Seals?</strong> Seals are binding contracts between two players. Once signed, the game automatically tracks and enforces the terms. Breaching a Seal marks the offending player as Persona Non Grata and permanently marks them as a Seal-breaker.
                            </p>
                            <p>
                                <strong>What can you write?</strong> The compiler currently supports actions involving the <strong>Citadel</strong> (entering/leaving), <strong>City Travel & Bans</strong> (e.g. travel to a city or avoid a city), <strong>Items</strong> (buying/selling cars, houses, airplanes), and <strong>Skills</strong> (reaching target attack/defense/driving points).
                            </p>
                            <p>
                                <strong>Examples of what you can write (click to fill):</strong>
                            </p>
                            <ul className="seals-informal-examples">
                                <li onClick={() => setRawText("If I enter the Citadel, he must travel to Moscow.")}>
                                    <code>"If I enter the Citadel, he must travel to Moscow."</code> — <em>(Citadel trigger + Travel obligation)</em>
                                </li>
                                <li onClick={() => setRawText("Should he arrive in Rome, he must not set foot in New York.")}>
                                    <code>"Should he arrive in Rome, he must not set foot in New York."</code> — <em>(Travel trigger + City ban)</em>
                                </li>
                                <li onClick={() => setRawText("If I acquire a house, he must sell a car.")}>
                                    <code>"If I acquire a house, he must sell a car."</code> — <em>(Asset purchase trigger + Asset sale)</em>
                                </li>
                                <li onClick={() => setRawText("Upon signing this Seal, he must raise his attack skill to 500 points.")}>
                                    <code>"Upon signing this Seal, he must raise his attack skill to 500 points."</code> — <em>(Immediate trigger + Skill target)</em>
                                </li>
                            </ul>
                            <p className="seals-informal-note">
                                <em>(Note for testing: Combat/kills, exfiltration missions, and cash transfers will be supported once those features are wired into the game events).</em>
                            </p>
                        </div>

                        <div className="seals-form">
                            <div className="seals-form-row">
                                <label className="seals-form-label">COUNTERPARTY</label>
                                <input
                                    className="seals-input"
                                    type="text"
                                    placeholder="Username of the other Elite"
                                    autoComplete="new-password"
                                    value={counterparty}
                                    onChange={e => setCounterparty(e.target.value)}
                                />
                            </div>

                            <div className="seals-form-row">
                                <label className="seals-form-label">TERMS</label>
                                <textarea
                                    className="seals-input seals-textarea"
                                    placeholder='e.g. "If I enter the Citadel, he must travel to Rome."'
                                    maxLength={tabData.raw_text_max_len}
                                    rows={3}
                                    value={rawText}
                                    onChange={e => setRawText(e.target.value)}
                                />
                                <div className="seals-char-count">
                                    {rawText.length} / {tabData.raw_text_max_len}
                                </div>
                            </div>

                            <div className="seals-form-inline">
                                <div className="seals-form-row">
                                    <label className="seals-form-label">DEADLINE (DAYS)</label>
                                    <input
                                        className="seals-input seals-input-small"
                                        type="number"
                                        min={tabData.deadline_min_days}
                                        max={tabData.deadline_max_days}
                                        value={deadlineDays}
                                        onChange={e => setDeadlineDays(e.target.value)}
                                    />
                                </div>
                                <div className="seals-form-row">
                                    <label className="seals-form-label">PENALTY ON BREACH</label>
                                    <select
                                        className="seals-input seals-input-small"
                                        value={penaltyDays}
                                        onChange={e => setPenaltyDays(e.target.value)}
                                    >
                                        {tabData.penalty_choices.map(days => (
                                            <option key={days} value={days}>
                                                Persona non grata — {days} days
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            {formError && <div className="seals-error">{formError}</div>}

                            <button
                                className="btn-seal-primary"
                                disabled={busy || !counterparty.trim() || !rawText.trim()}
                                onClick={handleCompile}
                            >
                                {busy ? 'PROCESSING...' : 'PREVIEW SEAL'}
                            </button>
                        </div>
                    </>
                )}
            </div>

            {/* ── Presented to you ── */}
            {tabData.incoming.length > 0 && (
                <div className="seals-section">
                    <div className="seals-section-title">PRESENTED TO YOU</div>
                    {tabData.incoming.map(seal => (
                        <SealCard
                            key={seal.id}
                            seal={seal}
                            username={userPreviewData.username}
                            onAction={handleAction}
                            busy={busy}
                        />
                    ))}
                </div>
            )}

            {/* ── Awaiting signature ── */}
            {tabData.outgoing.length > 0 && (
                <div className="seals-section">
                    <div className="seals-section-title">AWAITING SIGNATURE</div>
                    {tabData.outgoing.map(seal => (
                        <SealCard
                            key={seal.id}
                            seal={seal}
                            username={userPreviewData.username}
                            onAction={handleAction}
                            busy={busy}
                        />
                    ))}
                </div>
            )}

            {/* ── Bound seals ── */}
            <div className="seals-section">
                <div className="seals-section-title">BOUND SEALS</div>
                {tabData.active.length === 0 ? (
                    <p className="seals-note">No Seal binds you at present.</p>
                ) : (
                    tabData.active.map(seal => (
                        <SealCard
                            key={seal.id}
                            seal={seal}
                            username={userPreviewData.username}
                            onAction={handleAction}
                            busy={busy}
                        />
                    ))
                )}
            </div>

            {/* ── Records ── */}
            {tabData.history.length > 0 && (
                <div className="seals-section">
                    <div className="seals-section-title">RECORDS</div>
                    {tabData.history.map(seal => (
                        <SealCard
                            key={seal.id}
                            seal={seal}
                            username={userPreviewData.username}
                            onAction={handleAction}
                            busy={busy}
                        />
                    ))}
                </div>
            )}
        </div>
    )
}

export default SealsTab
