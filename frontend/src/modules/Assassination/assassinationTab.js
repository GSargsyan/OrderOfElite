import React, { useState, useEffect, useContext, useCallback } from 'react'
import { request, formatSeconds, formatMoney } from 'modules/Base'
import { UserPreviewCtx } from 'modules/Dashboard'
import { CoinsIcon } from 'components/icons'

const SEARCH_COST_CITY = 1
const SEARCH_COST_GLOBAL = 5

const ATTACK_TYPES = [
    {
        key: 'regular',
        label: 'Regular',
        description: 'Direct engagement. Highest chance of a decisive outcome, for both parties.',
    },
    {
        key: 'driveby',
        label: 'Drive-by',
        description: 'Reduced exposure. Reduced effect, for both parties.',
    },
    {
        key: 'sniping',
        label: 'Long Range Sniping',
        description: 'Minimal exposure. Requires a significant advantage to secure an elimination.',
    },
]

function formatResult(entry) {
    if (!entry.found) {
        return `Not in ${entry.searcher_city}`
    }
    if (entry.result_status === 'citadel') {
        return `${entry.result_city} — Inside Citadel`
    }
    if (entry.result_status === 'flight') {
        return `${entry.result_city} — currently in flight`
    }
    return entry.result_city
}

function SearchSection() {
    const [targetName, setTargetName] = useState('')
    const [history, setHistory] = useState([])
    const [error, setError] = useState(null)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [now, setNow] = useState(() => Math.floor(Date.now() / 1000))
    const { userPreviewData, updateUserPreviewData } = useContext(UserPreviewCtx)

    const loadHistory = useCallback(() => {
        request({ url: 'assassination/get_search_history', method: 'POST' })
            .then(res => setHistory(res.data))
            .catch(err => console.error('Search history load error:', err))
    }, [])

    useEffect(() => {
        loadHistory()
    }, [loadHistory])

    useEffect(() => {
        const interval = setInterval(() => setNow(Math.floor(Date.now() / 1000)), 1000)
        return () => clearInterval(interval)
    }, [])

    const eliteCoins = userPreviewData?.elite_coins ?? 0

    const handleSearch = (searchType) => {
        if (isSubmitting) return
        if (!targetName.trim()) {
            setError('Enter a target name')
            return
        }

        setError(null)
        setIsSubmitting(true)
        request({
            url: 'assassination/search',
            method: 'POST',
            data: { username: targetName.trim(), search_type: searchType },
        })
            .then(() => {
                setTargetName('')
                loadHistory()
                updateUserPreviewData()
            })
            .catch(err => {
                setError(err.response?.data?.message || 'Search failed.')
            })
            .finally(() => setIsSubmitting(false))
    }

    return (
        <div className="search-section">
            <div className="profile-section-title">Search</div>
            <p className="skills-intro-text">
                Locate a target before attempting an assassination. A City search reports
                whether the target is currently in your city; a Global search locates them
                in any city. Results take 20 minutes to come through and reflect the
                target's status at the moment the search was made. A successful search
                remains valid grounds for an attempt for 20 minutes after it resolves.
            </p>

            <div className="assassination-form search-form">
                <div className="assassination-field">
                    <label className="assassination-label">Target Name</label>
                    <input
                        type="text"
                        className="assassination-input"
                        placeholder="Enter target's name"
                        value={targetName}
                        onChange={e => setTargetName(e.target.value)}
                        disabled={isSubmitting}
                    />
                </div>

                {error && <div className="profile-error">{error}</div>}

                <div className="search-buttons-row">
                    <button
                        className="btn-search"
                        disabled={isSubmitting || eliteCoins < SEARCH_COST_CITY || !targetName.trim()}
                        onClick={() => handleSearch('city')}
                    >
                        Search City (1 <CoinsIcon className="inline-coin-icon" />)
                    </button>
                    <button
                        className="btn-search"
                        disabled={isSubmitting || eliteCoins < SEARCH_COST_GLOBAL || !targetName.trim()}
                        onClick={() => handleSearch('global')}
                    >
                        Search Global (5 <CoinsIcon className="inline-coin-icon" />)
                    </button>
                </div>
            </div>

            <table className="elites-table search-history-table">
                <thead>
                    <tr><th>Target</th><th>Type</th><th>Result</th><th>As Of</th></tr>
                </thead>
                <tbody>
                    {history.length === 0 && (
                        <tr><td colSpan={4} className="profile-empty-note">No searches yet.</td></tr>
                    )}
                    {history.map(entry => {
                        const remaining = Math.max(0, entry.ready_at - now)
                        return (
                            <tr key={entry.id}>
                                <td>{entry.target}</td>
                                <td>{entry.search_type === 'global' ? 'Global' : 'City'} ({entry.cost} <CoinsIcon className="inline-coin-icon" />)</td>
                                <td>
                                    {entry.ready ? (
                                        formatResult(entry)
                                    ) : (
                                        <span className="profile-cd-remaining">Ready in {formatSeconds(remaining)}</span>
                                    )}
                                </td>
                                <td>
                                    {entry.ready
                                        ? new Date(entry.created_at * 1000).toLocaleString()
                                        : '—'}
                                </td>
                            </tr>
                        )
                    })}
                </tbody>
            </table>
        </div>
    )
}

function GearInfoRow({ label, gun, car }) {
    return (
        <div className="attack-gear-row">
            <span className="attack-gear-label">{label}</span>
            <span className="attack-gear-value">{gun || 'No firearm equipped'}</span>
            <span className="attack-gear-value">{car || 'No vehicle equipped'}</span>
        </div>
    )
}

function AttackSection() {
    const { updateUserPreviewData } = useContext(UserPreviewCtx)

    const [targetName, setTargetName] = useState('')
    const [operationalBudget, setOperationalBudget] = useState('')
    const [attackType, setAttackType] = useState('regular')
    const [panelData, setPanelData] = useState(null)
    const [loadingPanel, setLoadingPanel] = useState(false)
    const [submitError, setSubmitError] = useState(null)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [result, setResult] = useState(null)
    const [now, setNow] = useState(() => Math.floor(Date.now() / 1000))

    useEffect(() => {
        const interval = setInterval(() => setNow(Math.floor(Date.now() / 1000)), 1000)
        return () => clearInterval(interval)
    }, [])

    // Debounced lookup — refetches on every keystroke, including the
    // initial empty value (which still returns the attacker's own gear
    // and cooldown status).
    useEffect(() => {
        setLoadingPanel(true)
        const handle = setTimeout(() => {
            request({
                url: 'assassination/get_attack_panel_data',
                method: 'POST',
                data: { username: targetName.trim() },
            })
                .then(res => {
                    setPanelData(res.data)
                    setLoadingPanel(false)
                })
                .catch(() => setLoadingPanel(false))
        }, 400)
        return () => clearTimeout(handle)
    }, [targetName])

    const cooldownRemaining = panelData?.cooldown_until
        ? Math.max(0, Math.round(panelData.cooldown_until - now))
        : 0
    const searchExpired = panelData?.search_expires_at
        ? panelData.search_expires_at - now <= 0
        : false
    const hasValidSearch = Boolean(panelData?.has_valid_search) && !searchExpired
    const onSharedMission = Boolean(panelData?.on_shared_mission)
    const canEngage = hasValidSearch || onSharedMission
    const budgetNum = parseInt(operationalBudget, 10)

    const canAttack = Boolean(
        targetName.trim() &&
        budgetNum > 0 &&
        canEngage &&
        !panelData?.target?.is_dead &&
        cooldownRemaining <= 0 &&
        !isSubmitting
    )

    const handleAttack = () => {
        if (!canAttack) return

        setSubmitError(null)
        setIsSubmitting(true)
        request({
            url: 'assassination/attempt',
            method: 'POST',
            data: {
                username: targetName.trim(),
                budget: budgetNum,
                attack_type: attackType,
            },
        })
            .then(res => {
                setResult(res.data)
                setIsSubmitting(false)
                updateUserPreviewData()
                request({
                    url: 'assassination/get_attack_panel_data',
                    method: 'POST',
                    data: { username: targetName.trim() },
                }).then(r => setPanelData(r.data))
            })
            .catch(err => {
                setSubmitError(err.response?.data?.message || 'The operation failed.')
                setIsSubmitting(false)
            })
    }

    let targetNote = null
    if (targetName.trim() && !loadingPanel) {
        if (panelData?.target?.is_dead) {
            targetNote = 'This operative is already deceased.'
        } else if (onSharedMission) {
            targetNote = 'No search required — you are on an active operation together.'
        } else if (!hasValidSearch) {
            targetNote = 'No current intelligence on this target. Conduct a search first.'
        }
    }

    return (
        <div className="attack-section">
            <div className="profile-section-title">Engage</div>

            <div className="attack-gear-panel">
                <GearInfoRow
                    label="You"
                    gun={panelData?.attacker?.gun}
                    car={panelData?.attacker?.car}
                />
                {panelData?.target && (
                    <GearInfoRow
                        label="Target"
                        gun={panelData.target.gun}
                        car={panelData.target.car}
                    />
                )}
            </div>

            <div className="assassination-form">
                <div className="assassination-field">
                    <label className="assassination-label">Target Name</label>
                    <input
                        type="text"
                        className="assassination-input"
                        placeholder="Enter target's name"
                        value={targetName}
                        onChange={e => { setTargetName(e.target.value); setResult(null) }}
                        disabled={isSubmitting}
                    />
                </div>

                <div className="assassination-field">
                    <label className="assassination-label">Operational Budget</label>
                    <input
                        type="number"
                        className="assassination-input"
                        placeholder="$0"
                        min="0"
                        value={operationalBudget}
                        onChange={e => setOperationalBudget(e.target.value)}
                        disabled={isSubmitting}
                    />
                </div>

                <div className="assassination-field">
                    <label className="assassination-label">Attack Type</label>
                    <div className="attack-type-options">
                        {ATTACK_TYPES.map(t => (
                            <button
                                key={t.key}
                                type="button"
                                className={`attack-type-option ${attackType === t.key ? 'selected' : ''}`}
                                onClick={() => setAttackType(t.key)}
                                disabled={isSubmitting}
                            >
                                <span className="attack-type-option-label">{t.label}</span>
                                <span className="attack-type-option-desc">{t.description}</span>
                            </button>
                        ))}
                    </div>
                </div>

                {targetNote && <div className="profile-error">{targetNote}</div>}
                {cooldownRemaining > 0 && (
                    <div className="profile-error">
                        Recovering from your last operation. Available in {formatSeconds(cooldownRemaining)}
                    </div>
                )}
                {submitError && <div className="profile-error">{submitError}</div>}

                <button
                    className="btn-assassination"
                    disabled={!canAttack}
                    onClick={handleAttack}
                >
                    {isSubmitting ? 'ENGAGING...' : 'ATTEMPT ASSASSINATION'}
                </button>
            </div>

            {result && (
                <div className="attack-result-panel">
                    <div className="attack-result-row">
                        <span className="attack-result-label">Your Health</span>
                        <span className="attack-result-value">{result.attacker_health}%</span>
                    </div>
                    <div className="attack-result-row">
                        <span className="attack-result-label">Target's Health</span>
                        <span className="attack-result-value">{result.defender_health}%</span>
                    </div>

                    {result.target_eliminated ? (
                        <div className="attack-result-banner">
                            TARGET ELIMINATED
                            {result.money_looted > 0 && (
                                <div className="attack-result-loot">
                                    {formatMoney(result.money_looted)} recovered from the target
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="attack-result-outcome">
                            {result.outcome === 'backfire'
                                ? 'The operation was repelled.'
                                : 'The target survived the encounter.'}
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

function AssassinationTab() {
    return (
        <div className="assassination-tab">
            <SearchSection />
            <AttackSection />
        </div>
    )
}

export default AssassinationTab
