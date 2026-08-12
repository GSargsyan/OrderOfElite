import React, { useState, useEffect, useContext, useCallback } from 'react'
import { request, formatMoney, formatSeconds } from 'modules/Base'
import { UserPreviewCtx } from 'modules/Dashboard'

const SKILL_LABELS = {
    attack: { label: 'Attack', icon: '⚔' },
    defense: { label: 'Defense', icon: '🛡' },
    driving: { label: 'Driving', icon: '🏎' },
}

function healthTier(health) {
    if (health <= 50) return 'low'
    if (health <= 99) return 'mid'
    return 'full'
}

/**
 * Two-step confirm heal button, mirroring LeaveCitadelButton's
 * confirm/click-again pattern from citadelTab.js.
 */
function HealButton({ health, costPerPoint, onHealed }) {
    const [confirming, setConfirming] = useState(false)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (!confirming) return
        const timer = setTimeout(() => setConfirming(false), 4000)
        return () => clearTimeout(timer)
    }, [confirming])

    const missingHp = 100 - health
    const cost = missingHp * costPerPoint

    const handleClick = () => {
        if (isSubmitting) return
        if (!confirming) {
            setConfirming(true)
            return
        }

        setError(null)
        setIsSubmitting(true)
        request({ url: 'users/heal', method: 'POST' })
            .then(res => {
                if (onHealed) onHealed(res.data)
            })
            .catch(err => {
                setError(err.response?.data?.message || 'Healing failed.')
            })
            .finally(() => {
                setIsSubmitting(false)
                setConfirming(false)
            })
    }

    return (
        <div className="profile-heal-container">
            {error && <div className="profile-error">{error}</div>}
            <p className="profile-heal-cost-note">
                Healing to full health costs {formatMoney(cost)} ({missingHp} HP &times; {formatMoney(costPerPoint)} per point).
            </p>
            <button
                className={`btn-heal ${confirming ? 'confirming' : ''}`}
                disabled={isSubmitting}
                onClick={handleClick}
            >
                {isSubmitting
                    ? 'HEALING...'
                    : confirming
                        ? `CONFIRM — ${formatMoney(cost)}`
                        : 'HEAL AT THE HOSPITAL'}
            </button>
        </div>
    )
}

/**
 * Mission and skill cooldown rows. cd_remaining values from the backend are
 * either 0 (ready) or an epoch timestamp in the future (same convention as
 * skillsTab.js / MissionsController).
 */
function CooldownRows({ missions, skillsCooldowns }) {
    const [now, setNow] = useState(() => Math.floor(Date.now() / 1000))

    useEffect(() => {
        const interval = setInterval(() => setNow(Math.floor(Date.now() / 1000)), 1000)
        return () => clearInterval(interval)
    }, [])

    const renderRow = (key, label, allowed, cdTimestamp, extraNote) => {
        const remaining = Math.max(0, (cdTimestamp || 0) - now)
        return (
            <tr key={key}>
                <td>{label}</td>
                <td>
                    {!allowed
                        ? <span className="profile-cd-locked">Locked</span>
                        : extraNote
                            ? <span className="profile-cd-locked">{extraNote}</span>
                            : remaining <= 0
                                ? <span className="profile-cd-ready">Ready</span>
                                : <span className="profile-cd-remaining">{formatSeconds(remaining)}</span>}
                </td>
            </tr>
        )
    }

    return (
        <table className="elites-table">
            <thead>
                <tr><th>Activity</th><th>Status</th></tr>
            </thead>
            <tbody>
                {renderRow('stakeout', 'Stakeout', missions.stakeout.allowed, missions.stakeout.cd_remaining)}
                {renderRow('recon_op', 'Recon Op', missions.recon_op.allowed, missions.recon_op.cd_remaining)}
                {renderRow('extraction', 'Extraction', missions.extraction.allowed, missions.extraction.cd_remaining,
                    missions.extraction.mode === 'active' ? 'In progress' : null)}
                {renderRow('free_training', 'Free Training', true, skillsCooldowns.attack_free_cd)}
                {renderRow('pro_training', 'Professional Training', true, skillsCooldowns.attack_pro_cd)}
            </tbody>
        </table>
    )
}

function ProfileTab() {
    const [profileData, setProfileData] = useState(null)
    const { updateUserPreviewData } = useContext(UserPreviewCtx)

    const loadProfile = useCallback(() => {
        request({ url: 'dashboard/get_profile_tab_data', method: 'POST' })
            .then(res => setProfileData(res.data))
            .catch(err => console.error('ProfileTab load error:', err))
    }, [])

    useEffect(() => {
        loadProfile()
    }, [loadProfile])

    if (!profileData) {
        return <div className="loading-text">LOADING PROFILE...</div>
    }

    const handleHealed = () => {
        loadProfile()
        updateUserPreviewData()
    }

    const hasItems = Object.keys(profileData.items_by_city).length > 0
        || profileData.guns.length > 0
        || profileData.airplanes.length > 0

    return (
        <div className="profile-tab">
            {/* ── Header ── */}
            <div className="profile-section">
                <div className="profile-header-row">
                    <h2 className="profile-username">{profileData.username}</h2>
                    <span className="profile-rank">Rank {profileData.rank} ({Math.floor(profileData.rank_progress)}%)</span>
                </div>
                <div className="profile-status-line">
                    {profileData.in_flight && profileData.flight_data ? (
                        <span>In flight: {profileData.flight_data.origin_city} &rarr; {profileData.flight_data.destination_city}</span>
                    ) : (
                        <span>
                            In {profileData.city}
                            {profileData.in_citadel && (
                                <span className="user-preview-citadel-badge" style={{ marginLeft: 8 }}>🏛 CITADEL</span>
                            )}
                        </span>
                    )}
                </div>
            </div>

            {/* ── Skills ── */}
            <div className="profile-section">
                <div className="profile-section-title">Skills</div>
                <table className="elites-table">
                    <thead>
                        <tr><th>Skill</th><th>Base</th><th>Multiplier</th><th>Effective</th></tr>
                    </thead>
                    <tbody>
                        {Object.keys(SKILL_LABELS).map(key => (
                            <tr key={key}>
                                <td>{SKILL_LABELS[key].icon} {SKILL_LABELS[key].label}</td>
                                <td>{profileData[`base_${key}_points`]}</td>
                                <td>{profileData[`${key}_multiplier`]}x</td>
                                <td>{profileData[`${key}_points`]}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* ── Health ── */}
            <div className="profile-section">
                <div className="profile-section-title">Health</div>
                <div className={`profile-hp profile-hp--${healthTier(profileData.health)}`}>{profileData.health}%</div>
                {profileData.health < 100 && (
                    <HealButton
                        health={profileData.health}
                        costPerPoint={profileData.heal_cost_per_point}
                        onHealed={handleHealed}
                    />
                )}
            </div>

            {/* ── Kills ── */}
            <div className="profile-section">
                <div className="profile-section-title">Kills</div>
                <div className="profile-kills-count">{profileData.kills}</div>
            </div>

            {/* ── Items across all cities ── */}
            <div className="profile-section">
                <div className="profile-section-title">Items</div>
                {!hasItems ? (
                    <p className="profile-empty-note">No property held anywhere.</p>
                ) : (
                    <>
                        {Object.entries(profileData.items_by_city).map(([cityName, bucket]) => (
                            <div className="profile-city-items" key={cityName}>
                                <div className="profile-city-name">{cityName}</div>
                                <ul className="profile-item-list">
                                    {bucket.houses.map((h, i) => (
                                        <li key={`h-${i}`}>{h.name}{h.is_equipped && ' (equipped)'}</li>
                                    ))}
                                    {bucket.cars.map((c, i) => (
                                        <li key={`c-${i}`}>{c.name}{c.is_equipped && ' (equipped)'}</li>
                                    ))}
                                </ul>
                            </div>
                        ))}
                        {(profileData.guns.length > 0 || profileData.airplanes.length > 0) && (
                            <div className="profile-city-items">
                                <div className="profile-city-name">Player-Bound</div>
                                <ul className="profile-item-list">
                                    {profileData.guns.map((g, i) => (
                                        <li key={`g-${i}`}>{g.name}{g.is_equipped && ' (equipped)'}</li>
                                    ))}
                                    {profileData.airplanes.map((a, i) => (
                                        <li key={`a-${i}`}>{a.name}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </>
                )}
            </div>

            {/* ── Black Market ── */}
            <div className="profile-section">
                <div className="profile-section-title">Black Market</div>
                <p className="profile-bm-summary">
                    {profileData.black_market.total_professionals} / {profileData.black_market.max_professionals} professionals employed
                </p>
                {profileData.black_market.drugs.length > 0 ? (
                    <table className="elites-table">
                        <thead><tr><th>Drug</th><th>Stash</th><th>Price</th></tr></thead>
                        <tbody>
                            {profileData.black_market.drugs.map(d => (
                                <tr key={d.drug_type}>
                                    <td>{d.name}</td>
                                    <td>{d.stash_qty.toFixed(2)}</td>
                                    <td>{formatMoney(Math.round(d.current_price))}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                ) : (
                    <p className="profile-empty-note">No production lines unlocked yet.</p>
                )}
            </div>

            {/* ── Cooldowns ── */}
            <div className="profile-section">
                <div className="profile-section-title">Cooldowns</div>
                <CooldownRows missions={profileData.missions} skillsCooldowns={profileData.skills_cooldowns} />
            </div>
        </div>
    )
}

export default ProfileTab
