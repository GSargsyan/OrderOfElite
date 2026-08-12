import React, { useState, useEffect, useContext, useCallback } from 'react'
import { request, formatSeconds } from 'modules/Base'
import { UserPreviewCtx } from 'modules/Dashboard'

const SEARCH_COST_CITY = 1
const SEARCH_COST_GLOBAL = 5

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
                target's status at the moment the search was made.
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
                        Search City (1 🪙)
                    </button>
                    <button
                        className="btn-search"
                        disabled={isSubmitting || eliteCoins < SEARCH_COST_GLOBAL || !targetName.trim()}
                        onClick={() => handleSearch('global')}
                    >
                        Search Global (5 🪙)
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
                                <td>{entry.search_type === 'global' ? 'Global' : 'City'} ({entry.cost} 🪙)</td>
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

function AssassinationTab() {
    const [eliteName, setEliteName] = useState('')
    const [operationalBudget, setOperationalBudget] = useState('')

    return (
        <div className="assassination-tab">
            <SearchSection />

            <div className="not-implemented-tab">
                <div className="not-implemented-icon">🎯</div>
                <h2 className="not-implemented-title">NOT IMPLEMENTED</h2>

                <div className="assassination-form">
                    <div className="assassination-field">
                        <label className="assassination-label">ELITE NAME</label>
                        <input
                            type="text"
                            className="assassination-input"
                            placeholder="Enter target's name"
                            value={eliteName}
                            onChange={e => setEliteName(e.target.value)}
                        />
                    </div>

                    <div className="assassination-field">
                        <label className="assassination-label">OPERATIONAL BUDGET</label>
                        <input
                            type="number"
                            className="assassination-input"
                            placeholder="$0"
                            min="0"
                            value={operationalBudget}
                            onChange={e => setOperationalBudget(e.target.value)}
                        />
                    </div>

                    <button className="btn-assassination" disabled>
                        ATTEMPT ASSASSINATION
                    </button>
                </div>
            </div>
        </div>
    )
}

export default AssassinationTab
