import React, { useState, useEffect, useContext, useCallback } from 'react'
import { request } from 'modules/Base'
import { UserPreviewCtx } from 'modules/Dashboard'

// Duration presets, in minutes
const STAY_PRESETS = [
    { label: '30m', minutes: 30 },
    { label: '1h', minutes: 60 },
    { label: '2h', minutes: 120 },
    { label: '4h', minutes: 240 },
    { label: '8h', minutes: 480 },
    { label: '12h', minutes: 720 },
]

// Live countdown formatter: "Xh Ym Zs" / "Ym Zs" / "Zs"
export function formatCitadelCountdown(totalSeconds) {
    const h = Math.floor(totalSeconds / 3600)
    const m = Math.floor((totalSeconds % 3600) / 60)
    const s = totalSeconds % 60
    if (h > 0) return `${h}h ${m}m ${s}s`
    if (m > 0) return `${m}m ${s}s`
    return `${s}s`
}

/**
 * Two-step departure button, shared by the Citadel tab and the
 * blocked-tab overlay. First click asks for confirmation, second
 * click submits. onLeft(tabData) fires after a successful departure.
 */
export function LeaveCitadelButton({ onLeft }) {
    const [confirming, setConfirming] = useState(false)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [error, setError] = useState(null)

    // Confirmation request expires if not acted upon
    useEffect(() => {
        if (!confirming) return
        const timer = setTimeout(() => setConfirming(false), 4000)
        return () => clearTimeout(timer)
    }, [confirming])

    const handleClick = () => {
        if (isSubmitting) return
        if (!confirming) {
            setConfirming(true)
            return
        }

        setError(null)
        setIsSubmitting(true)
        request({ url: 'citadel/leave', method: 'POST' })
            .then(res => {
                if (onLeft) onLeft(res.data)
            })
            .catch(err => {
                setError(err.response?.data?.message || 'Departure failed.')
            })
            .finally(() => {
                setIsSubmitting(false)
                setConfirming(false)
            })
    }

    return (
        <div className="citadel-leave-container">
            {error && <div className="citadel-error">{error}</div>}
            <button
                className={`btn-citadel-leave ${confirming ? 'confirming' : ''}`}
                disabled={isSubmitting}
                onClick={handleClick}
            >
                {isSubmitting
                    ? 'DEPARTING...'
                    : confirming
                        ? 'CONFIRM DEPARTURE'
                        : 'LEAVE THE CITADEL'}
            </button>
            <div className="citadel-leave-hint">
                {confirming
                    ? 'Departure sets a reentry restriction. Confirm to proceed.'
                    : ''}
            </div>
        </div>
    )
}

function CitadelTab() {
    const [tabData, setTabData] = useState(null)
    const [stayHours, setStayHours] = useState(1)
    const [stayMinutes, setStayMinutes] = useState(0)
    const [error, setError] = useState(null)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [stayCountdown, setStayCountdown] = useState(0)
    const [cooldownCountdown, setCooldownCountdown] = useState(0)

    const { updateUserPreviewData } = useContext(UserPreviewCtx)

    const applyTabData = useCallback((data) => {
        setTabData(data)

        const now = Math.floor(Date.now() / 1000)
        setStayCountdown(data.in_citadel
            ? Math.max(0, Math.floor(data.stay_until - now))
            : 0)
        setCooldownCountdown(data.cooldown_until > 0
            ? Math.max(0, Math.floor(data.cooldown_until - now))
            : 0)
    }, [])

    const loadTabData = useCallback(() => {
        request({ url: 'citadel/get_tab_data', method: 'POST' })
            .then(res => applyTabData(res.data))
            .catch(err => console.error('CitadelTab load error:', err))
    }, [applyTabData])

    useEffect(() => {
        loadTabData()
    }, [loadTabData])

    // Countdown timers
    useEffect(() => {
        if (stayCountdown <= 0 && cooldownCountdown <= 0) return

        const interval = setInterval(() => {
            setStayCountdown(v => {
                const next = Math.max(0, v - 1)
                if (next === 0 && v > 0) {
                    // Stay just expired — refresh state
                    setTimeout(() => {
                        loadTabData()
                        updateUserPreviewData()
                    }, 1500)
                }
                return next
            })
            setCooldownCountdown(v => Math.max(0, v - 1))
        }, 1000)

        return () => clearInterval(interval)
    }, [stayCountdown, cooldownCountdown, loadTabData, updateUserPreviewData])

    const maxStayHours = tabData
        ? Math.floor(tabData.max_stay_minutes / 60)
        : 12

    const handleHoursChange = (value) => {
        let h = parseInt(value, 10)
        if (isNaN(h)) h = 0
        h = Math.min(maxStayHours, Math.max(0, h))
        setStayHours(h)
        if (h === maxStayHours) setStayMinutes(0)
    }

    const handleMinutesChange = (value) => {
        let m = parseInt(value, 10)
        if (isNaN(m)) m = 0
        m = Math.min(59, Math.max(0, m))
        if (stayHours === maxStayHours) m = 0
        setStayMinutes(m)
    }

    const handlePreset = (presetMinutes) => {
        setStayHours(Math.floor(presetMinutes / 60))
        setStayMinutes(presetMinutes % 60)
    }

    const totalMinutes = stayHours * 60 + stayMinutes

    const handleEnter = () => {
        if (isSubmitting) return
        setError(null)
        setIsSubmitting(true)

        request({
            url: 'citadel/enter',
            method: 'POST',
            data: { minutes: totalMinutes },
        })
            .then(res => {
                applyTabData(res.data)
                updateUserPreviewData()
            })
            .catch(err => {
                setError(err.response?.data?.message || 'Entry failed.')
            })
            .finally(() => setIsSubmitting(false))
    }

    const handleLeft = (data) => {
        applyTabData(data)
        updateUserPreviewData()
    }

    if (!tabData) {
        return <div className="loading-text">LOADING CITADEL DATA...</div>
    }

    const isDurationValid = totalMinutes >= tabData.min_stay_minutes
        && totalMinutes <= tabData.max_stay_minutes

    // Local time the doors would close behind the player
    const exitDate = new Date(Date.now() + totalMinutes * 60000)
    const exitTimeLabel = exitDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    const exitIsTomorrow = exitDate.getDate() !== new Date().getDate()

    const isInside = tabData.in_citadel
    const isOnCooldown = !isInside && cooldownCountdown > 0

    return (
        <div className="citadel-tab">
            {isInside ? (
                /* ── Inside the Citadel ── */
                <div className="citadel-inside-panel">
                    <div className="citadel-inside-icon">🏛</div>
                    <div className="citadel-inside-title">SANCTUARY IN EFFECT</div>
                    <div className="citadel-inside-subtitle">
                        Within these walls, no contract may be honored.
                        Defense ×{tabData.defense_multiplier} while the doors remain closed.
                    </div>
                    <div className="citadel-inside-countdown">
                        {stayCountdown > 0
                            ? formatCitadelCountdown(stayCountdown)
                            : 'Doors opening...'}
                    </div>
                    <div className="citadel-inside-countdown-label">UNTIL DEPARTURE</div>
                    <LeaveCitadelButton onLeft={handleLeft} />
                </div>
            ) : isOnCooldown ? (
                /* ── Reentry restriction ── */
                <div className="citadel-cooldown-panel">
                    <div className="citadel-cooldown-icon">⏱</div>
                    <div className="citadel-cooldown-title">REENTRY RESTRICTED</div>
                    <div className="citadel-cooldown-remaining">
                        The doors open to you again in {formatCitadelCountdown(cooldownCountdown)}
                    </div>
                </div>
            ) : (
                /* ── Entry form ── */
                <>
                    {tabData.persona_non_grata && (
                        <div className="citadel-png-notice">
                            ⚠ PERSONA NON GRATA — The Citadel's hospitality is
                            curtailed. Sanctuary is limited
                            to {Math.floor(tabData.max_stay_minutes / 60)} hours, and
                            departure sets
                            a {Math.floor(tabData.cooldown_minutes / 60)}-hour
                            reentry restriction.
                        </div>
                    )}
                    <div className="citadel-notice">
                        🏛 Within the Citadel walls, sanctuary is absolute. No business may be
                        conducted — Missions, Items, Black Market, Skills and Travel are
                        suspended until departure. Leaving sets
                        a {Math.floor(tabData.cooldown_minutes / 60)}-hour reentry restriction.
                    </div>

                    <div className="citadel-section">
                        <div className="citadel-section-title">DURATION OF STAY</div>

                        <div className="citadel-presets">
                            {STAY_PRESETS.filter(p => p.minutes <= tabData.max_stay_minutes).map(preset => (
                                <button
                                    key={preset.minutes}
                                    className={`citadel-preset-chip ${totalMinutes === preset.minutes ? 'selected' : ''}`}
                                    onClick={() => handlePreset(preset.minutes)}
                                >
                                    {preset.label}
                                </button>
                            ))}
                        </div>

                        <div className="citadel-duration-inputs">
                            <div className="citadel-duration-field">
                                <input
                                    type="number"
                                    min="0"
                                    max={maxStayHours}
                                    value={stayHours}
                                    onChange={e => handleHoursChange(e.target.value)}
                                />
                                <span className="citadel-duration-unit">HOURS</span>
                            </div>
                            <span className="citadel-duration-sep">:</span>
                            <div className="citadel-duration-field">
                                <input
                                    type="number"
                                    min="0"
                                    max="59"
                                    value={stayMinutes}
                                    disabled={stayHours === maxStayHours}
                                    onChange={e => handleMinutesChange(e.target.value)}
                                />
                                <span className="citadel-duration-unit">MINUTES</span>
                            </div>
                        </div>

                        <div className="citadel-until-line">
                            {isDurationValid
                                ? <>The doors close behind you until <span className="citadel-until-time">
                                    {exitTimeLabel}{exitIsTomorrow ? ' (tomorrow)' : ''}
                                  </span>.</>
                                : `Sanctuary is granted for ${tabData.min_stay_minutes} minutes to ${tabData.max_stay_minutes / 60} hours.`}
                        </div>
                    </div>

                    <div className="citadel-terms">
                        <div className="citadel-terms-item">
                            <span className="citadel-terms-label">PROTECTION</span>
                            <span className="citadel-terms-value">Defense ×{tabData.defense_multiplier}</span>
                        </div>
                        <div className="citadel-terms-item">
                            <span className="citadel-terms-label">REENTRY RESTRICTION</span>
                            <span className="citadel-terms-value">{Math.floor(tabData.cooldown_minutes / 60)}h after departure</span>
                        </div>
                    </div>

                    {error && <div className="citadel-error">{error}</div>}

                    <button
                        className="btn-citadel"
                        disabled={!isDurationValid || isSubmitting}
                        onClick={handleEnter}
                    >
                        {isSubmitting ? 'REQUESTING SANCTUARY...' : '🏛 ENTER THE CITADEL'}
                    </button>
                </>
            )}
        </div>
    )
}

export default CitadelTab
