import React, { useState, useEffect, useCallback } from 'react'
import { request, formatMoney } from 'modules/Base'
import { ChatBoard } from 'modules/Chat/chatBoard.js'

const CONSEQUENCE_LABELS = {
    'none': 'NO CONSEQUENCE SPECIFIED',
    'persona_non_grata': 'PERSONA NON GRATA',
    'blacklist': 'BLACKLIST',
}

/* Two-step confirmation button (same pattern as Seals). */
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

function CouncilRoster({ council, termStartedAt }) {
    return (
        <div className="council-section">
            <div className="council-section-title">CURRENT MEMBERS</div>
            {council.length === 0 ? (
                <p className="council-empty-state">
                    The Grand Council currently has no seated members. Seats are
                    filled automatically from the highest-ranked eligible players
                    every Monday.
                </p>
            ) : (
                <div className="council-roster">
                    {council.map(member => (
                        <div key={member.username} className="council-member-card">
                            <div className="council-member-name">{member.username.toUpperCase()}</div>
                            <div className="council-member-stats">
                                <span>RANK {member.rank}</span>
                                <span>{member.kills} KILLS</span>
                                <span>{formatMoney(member.net_worth)}</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}
            {termStartedAt > 0 && (
                <div className="council-note">
                    Seated since {new Date(termStartedAt * 1000).toLocaleDateString()}.
                    The roster is recomputed every Monday, 00:00 UTC.
                </div>
            )}
        </div>
    )
}

function ConditionBadges({ condition }) {
    if (condition.condition_type !== 'rule') return null

    let detail = null
    if (condition.consequence === 'persona_non_grata') {
        detail = `${CONSEQUENCE_LABELS[condition.consequence]} — ${condition.png_days} DAYS`
    } else if (condition.consequence === 'blacklist') {
        detail = `${CONSEQUENCE_LABELS[condition.consequence]} — ${formatMoney(condition.bounty_amount)} BOUNTY`
    } else {
        detail = CONSEQUENCE_LABELS[condition.consequence] || CONSEQUENCE_LABELS['none']
    }

    return (
        <div className="condition-badges">
            <span className="condition-badge condition-badge--rule">RULE</span>
            <span className="condition-badge">ON BREACH — {detail}</span>
        </div>
    )
}

function ConditionCard({ condition }) {
    return (
        <div className="condition-card">
            <div className="condition-card-title">{condition.title}</div>
            <div className="condition-card-content">{condition.content}</div>
            <ConditionBadges condition={condition} />
        </div>
    )
}

function OrderOfEliteDocument({ title, liveDocument }) {
    return (
        <div className="council-section">
            <div className="council-section-title">{title.toUpperCase()}</div>
            {!liveDocument ? (
                <p className="council-empty-state">
                    No version of the Order of Elite has been published.
                </p>
            ) : (
                <>
                    <div className="council-note">
                        Version {liveDocument.version_number} — published{' '}
                        {new Date(liveDocument.published_at * 1000).toLocaleDateString()}.
                    </div>
                    {liveDocument.conditions.map(condition => (
                        <ConditionCard key={condition.id} condition={condition} />
                    ))}
                </>
            )}
        </div>
    )
}

function PendingDraftPanel({ draft, onVote, onDiscard, busy }) {
    const canVote = !draft.is_author && !draft.viewer_vote && draft.status === 'peer_review'

    return (
        <div className="council-section council-draft-panel">
            <div className="council-section-title">PENDING DRAFT — VERSION {draft.version_number}</div>
            <div className="council-note">
                Authored by {draft.author}. Status: {draft.status.replace('_', ' ').toUpperCase()}.
            </div>

            {draft.status === 'peer_review' && (
                <div className="council-approval-tally">
                    {draft.approvals_count} OF {draft.peer_threshold} APPROVED &middot;{' '}
                    {draft.rejections_count} OF {draft.peer_threshold} REJECTED
                </div>
            )}

            {draft.conditions.map(condition => (
                <ConditionCard key={condition.id} condition={condition} />
            ))}

            <div className="council-draft-actions">
                {canVote && (
                    <>
                        <ConfirmButton
                            className="btn-seal-primary"
                            label="APPROVE"
                            confirmLabel="CONFIRM APPROVAL"
                            disabled={busy}
                            onConfirm={() => onVote('approve_draft', draft.id)}
                        />
                        <ConfirmButton
                            className="btn-seal-secondary"
                            label="REJECT"
                            confirmLabel="CONFIRM REJECTION"
                            disabled={busy}
                            onConfirm={() => onVote('reject_draft', draft.id)}
                        />
                    </>
                )}
                {draft.viewer_vote && (
                    <div className="council-note">
                        You voted to {draft.viewer_vote === 'approve' ? 'approve' : 'reject'} this draft.
                    </div>
                )}
                {draft.is_author && draft.status === 'draft' && (
                    <ConfirmButton
                        className="btn-seal-secondary"
                        label="DISCARD"
                        confirmLabel="CONFIRM DISCARD"
                        disabled={busy}
                        onConfirm={() => onDiscard(draft.id)}
                    />
                )}
            </div>
        </div>
    )
}

function ConditionFormRow({ condition, index, tabData, onChange, onRemove }) {
    return (
        <div className="condition-form-row">
            <div className="seals-form-row">
                <label className="seals-form-label">CONDITION {index + 1} — TITLE</label>
                <input
                    className="seals-input"
                    type="text"
                    value={condition.title}
                    onChange={e => onChange({ ...condition, title: e.target.value })}
                />
            </div>
            <div className="seals-form-row">
                <label className="seals-form-label">CONTENT</label>
                <textarea
                    className="seals-input seals-textarea"
                    rows={3}
                    value={condition.content}
                    onChange={e => onChange({ ...condition, content: e.target.value })}
                />
            </div>
            <div className="seals-form-inline">
                <div className="seals-form-row">
                    <label className="seals-form-label">TYPE</label>
                    <select
                        className="seals-input seals-input-small"
                        value={condition.condition_type}
                        onChange={e => onChange({ ...condition, condition_type: e.target.value })}
                    >
                        {tabData.condition_type_choices.map(([value, label]) => (
                            <option key={value} value={value}>{label.toUpperCase()}</option>
                        ))}
                    </select>
                </div>

                {condition.condition_type === 'rule' && (
                    <div className="seals-form-row">
                        <label className="seals-form-label">ON BREACH</label>
                        <select
                            className="seals-input seals-input-small"
                            value={condition.consequence}
                            onChange={e => onChange({ ...condition, consequence: e.target.value })}
                        >
                            {tabData.consequence_choices.map(([value, label]) => (
                                <option key={value} value={value}>{label.toUpperCase()}</option>
                            ))}
                        </select>
                    </div>
                )}

                {condition.condition_type === 'rule' && condition.consequence === 'persona_non_grata' && (
                    <div className="seals-form-row">
                        <label className="seals-form-label">DURATION</label>
                        <select
                            className="seals-input seals-input-small"
                            value={condition.png_days || ''}
                            onChange={e => onChange({ ...condition, png_days: e.target.value })}
                        >
                            <option value="" disabled>SELECT</option>
                            {tabData.png_penalty_days_choices.map(days => (
                                <option key={days} value={days}>{days} DAYS</option>
                            ))}
                        </select>
                    </div>
                )}

                {condition.condition_type === 'rule' && condition.consequence === 'blacklist' && (
                    <div className="seals-form-row">
                        <label className="seals-form-label">BOUNTY</label>
                        <select
                            className="seals-input seals-input-small"
                            value={condition.bounty_amount || ''}
                            onChange={e => onChange({ ...condition, bounty_amount: e.target.value })}
                        >
                            <option value="" disabled>SELECT</option>
                            {tabData.blacklist_bounty_choices.map(amount => (
                                <option key={amount} value={amount}>{formatMoney(amount)}</option>
                            ))}
                        </select>
                    </div>
                )}
            </div>

            <button className="btn-seal-secondary" onClick={() => onRemove(index)}>
                REMOVE CONDITION
            </button>
        </div>
    )
}

const EMPTY_CONDITION = {
    title: '',
    content: '',
    condition_type: 'informative',
    consequence: 'none',
    png_days: null,
    bounty_amount: null,
}

function DraftAuthoringForm({ draft, tabData, onSaveConditions, onSubmit, busy }) {
    const [conditions, setConditions] = useState(
        draft.conditions.length > 0
            ? draft.conditions.map(c => ({ ...c }))
            : [{ ...EMPTY_CONDITION }]
    )

    const updateCondition = (index, updated) => {
        const next = [...conditions]
        next[index] = updated
        setConditions(next)
    }

    const removeCondition = (index) => {
        setConditions(conditions.filter((_, i) => i !== index))
    }

    const addCondition = () => {
        setConditions([...conditions, { ...EMPTY_CONDITION }])
    }

    return (
        <div className="council-section council-draft-form">
            <div className="council-section-title">
                {draft.conditions.length > 0 ? 'EDIT DRAFT' : 'CREATE DRAFT'} — VERSION {draft.version_number}
            </div>
            <p className="council-note">
                The fixed title "Order of Elite" is applied automatically and is not
                editable. Add the conditions that make up this version below.
            </p>

            {conditions.map((condition, index) => (
                <ConditionFormRow
                    key={condition.id || `new-${index}`}
                    condition={condition}
                    index={index}
                    tabData={tabData}
                    onChange={updated => updateCondition(index, updated)}
                    onRemove={removeCondition}
                />
            ))}

            <button className="btn-seal-secondary" disabled={busy} onClick={addCondition}>
                ADD CONDITION
            </button>

            <div className="council-draft-actions">
                <button
                    className="btn-seal-primary"
                    disabled={busy || conditions.length === 0}
                    onClick={() => onSaveConditions(draft.id, conditions, () => onSubmit(draft.id))}
                >
                    {busy ? 'PROCESSING...' : 'SAVE AND SUBMIT FOR APPROVAL'}
                </button>
            </div>
        </div>
    )
}

function GrandCouncilTab() {
    const [tabData, setTabData] = useState(null)
    const [busy, setBusy] = useState(false)

    const loadTabData = useCallback(() => {
        request({ url: 'grand_council/get_tab_data', method: 'POST' })
            .then(res => setTabData(res.data))
            .catch(err => console.error('GrandCouncilTab load error:', err))
    }, [])

    useEffect(() => { loadTabData() }, [loadTabData])

    if (!tabData) {
        return <div className="loading-text">LOADING...</div>
    }

    const handleCreateDraft = () => {
        if (busy) return
        setBusy(true)
        request({ url: 'grand_council/create_draft', method: 'POST' })
            .then(() => loadTabData())
            .catch(err => alert(err.response?.data?.message || 'The draft could not be created.'))
            .finally(() => setBusy(false))
    }

    const handleVote = (action, versionId) => {
        if (busy) return
        setBusy(true)
        request({ url: `grand_council/${action}`, method: 'POST', data: { version_id: versionId } })
            .then(() => loadTabData())
            .catch(err => alert(err.response?.data?.message || 'The action could not be completed.'))
            .finally(() => setBusy(false))
    }

    const handleDiscard = (versionId) => {
        if (busy) return
        setBusy(true)
        request({ url: 'grand_council/discard_draft', method: 'POST', data: { version_id: versionId } })
            .then(() => loadTabData())
            .catch(err => alert(err.response?.data?.message || 'The draft could not be discarded.'))
            .finally(() => setBusy(false))
    }

    // Replaces all conditions on the draft with the given list, then runs
    // onDone (submission) once every write has completed in order.
    const handleSaveConditions = (versionId, conditions, onDone) => {
        if (busy) return
        setBusy(true)

        const existing = tabData.pending_draft.conditions

        const removals = existing
            .filter(existingCondition => !conditions.some(c => c.id === existingCondition.id))
            .map(existingCondition => () => request({
                url: 'grand_council/remove_condition',
                method: 'POST',
                data: { version_id: versionId, condition_id: existingCondition.id },
            }))

        const upserts = conditions.map(condition => () => request({
            url: condition.id ? 'grand_council/update_condition' : 'grand_council/add_condition',
            method: 'POST',
            data: {
                version_id: versionId,
                condition_id: condition.id,
                title: condition.title,
                content: condition.content,
                condition_type: condition.condition_type,
                consequence: condition.consequence,
                png_days: condition.png_days,
                bounty_amount: condition.bounty_amount,
            },
        }))

        const steps = [...removals, ...upserts]
        steps.reduce((chain, step) => chain.then(step), Promise.resolve())
            .then(() => onDone())
            .catch(err => {
                alert(err.response?.data?.message || 'The condition could not be saved.')
                loadTabData()
            })
            .finally(() => setBusy(false))
    }

    const handleSubmit = (versionId) => {
        request({ url: 'grand_council/submit_for_approval', method: 'POST', data: { version_id: versionId } })
            .then(() => loadTabData())
            .catch(err => alert(err.response?.data?.message || 'The draft could not be submitted.'))
    }

    const draft = tabData.pending_draft
    const showAuthoringForm = tabData.is_council_member && draft
        && draft.status === 'draft' && draft.is_author
    const showCreateOrEdit = tabData.is_council_member && !draft

    return (
        <div className="council-tab">
            <CouncilRoster council={tabData.council} termStartedAt={tabData.term_started_at} />

            <OrderOfEliteDocument title={tabData.order_of_elite_title} liveDocument={tabData.live_document} />

            {tabData.is_council_member && draft && !showAuthoringForm && (
                <PendingDraftPanel
                    draft={draft}
                    onVote={handleVote}
                    onDiscard={handleDiscard}
                    busy={busy}
                />
            )}

            {showAuthoringForm && (
                <DraftAuthoringForm
                    draft={draft}
                    tabData={tabData}
                    onSaveConditions={handleSaveConditions}
                    onSubmit={handleSubmit}
                    busy={busy}
                />
            )}

            {showCreateOrEdit && (
                <div className="council-section">
                    <button className="btn-seal-primary" disabled={busy} onClick={handleCreateDraft}>
                        {tabData.live_document ? 'EDIT ORDER OF ELITE' : 'CREATE ORDER OF ELITE'}
                    </button>
                    <p className="council-note">
                        This will be reviewed by at least three other current members,
                        then by the game's administrators, before it takes effect.
                        Enforcement of individual rules is applied manually and may
                        take 24-72 hours after publication.
                    </p>
                </div>
            )}

            <div className="council-section">
                <div className="council-section-title">COUNCIL CHAT</div>
                {tabData.is_council_member && tabData.council_chat_room_id ? (
                    <ChatBoard chatRoomId={tabData.council_chat_room_id} name="Grand Council" />
                ) : (
                    <p className="council-empty-state">
                        This channel is reserved for seated Grand Council members.
                    </p>
                )}
            </div>
        </div>
    )
}

export default GrandCouncilTab
