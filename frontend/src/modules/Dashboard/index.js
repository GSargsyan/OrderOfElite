// import axios from 'axios'
import React, { createContext, useState, useEffect, memo, useRef, useCallback } from 'react'

import ChatContainer from 'modules/Chat/chatContainer.js'
import MissionsTab from 'modules/Missions/missionsTab.js'
import SkillsTab from 'modules/Skills/skillsTab.js'
import BlackMarketTab from 'modules/BlackMarket/blackMarketTab.js'
import ItemsTab from 'modules/Items/itemsTab.js'
import NetworkingTab from 'modules/Networking/networkingTab.js'
import ProfileTab from 'modules/Profile/profileTab.js'
import TravelTab from 'modules/Travel/travelTab.js'
import FlightOverlay from 'modules/Travel/flightOverlay.js'
import CitadelTab from 'modules/Citadel/citadelTab.js'
import CitadelOverlay from 'modules/Citadel/citadelOverlay.js'
import AssassinationTab from 'modules/Assassination/assassinationTab.js'
import GrandCouncilTab from 'modules/GrandCouncil/grandCouncilTab.js'
import SealsTab from 'modules/Seals/sealsTab.js'
import PremiumTab from 'modules/Premium/premiumTab.js'
import UserProfileModal from 'modules/Dashboard/userProfile.js'
import { request, formatMoney } from 'modules/Base'
import Footer from 'modules/Home/footer'
import 'styles/dashboard.css'


export const UserPreviewCtx = createContext()

// Tabs that are blocked while the user is in-flight
const FLIGHT_BLOCKED_TABS = ['missions', 'skills', 'black_market', 'items', 'assassination']

// Tabs that are blocked while the user is inside the Citadel
const CITADEL_BLOCKED_TABS = ['missions', 'skills', 'black_market', 'items', 'travel', 'assassination']

function Dashboard() {
    const [activeTab, setActiveTab] = useState('dashboard')
    const [userPreviewData, setUserPreviewData] = useState(null)
    const [userProfileData, setUserProfileData] = useState(null)
    const [showUserProfileModal, setShowUserProfileModal] = useState(false)

    // chat states
    const [messageUser, setMessageUser] = useState(null)
    const [focusChatInput, setFocusChatInput] = useState(false)

    const updateUserPreviewData = useCallback(() => {
        request({
            'url': 'users/get_preview',
            'method': 'POST',
        })
            .then(response => {
                setUserPreviewData(response.data)
            })
    }, [])

    const tabComponents = {
        'dashboard': {
            'component': DashboardTab,
            'label': 'Dashboard',
            'props': {}
        },
        'profile': {
            'component': ProfileTab,
            'label': 'Profile',
            'props': {}
        },
        'missions': {
            'component': MissionsTab,
            'label': 'Missions',
            'props': {}
        },
        'skills': {
            'component': SkillsTab,
            'label': 'Skills',
            'props': {}
        },
        'black_market': {
            'component': BlackMarketTab,
            'label': 'Black Market',
            'props': {}
        },
        'items': {
            'component': ItemsTab,
            'label': 'Items',
            'props': {}
        },
        'travel': {
            'component': TravelTab,
            'label': 'Travel',
            'props': {}
        },
        'assassination': {
            'component': AssassinationTab,
            'label': 'Assassination',
            'props': {}
        },
        'citadel': {
            'component': CitadelTab,
            'label': 'Citadel',
            'props': {}
        },
        'grand_council': {
            'component': GrandCouncilTab,
            'label': 'Grand Council',
            'props': {}
        },
        'seals': {
            'component': SealsTab,
            'label': userPreviewData?.is_premium
                ? 'Seals'
                : <>Seals <span className="menu-premium-mark" title="Reserved for members">✦</span></>,
            'props': {}
        },
        'premium': {
            'component': PremiumTab,
            'label': 'Premium',
            'props': {}
        },
        'networking': {
            'component': NetworkingTab,
            'label': 'Networking',
            'props': {
                'setUserProfileData': setUserProfileData,
                'setShowUserProfileModal': setShowUserProfileModal,
            }
        },
    }

    useEffect(() => {
        updateUserPreviewData()
    }, [])

    const isInFlight = userPreviewData?.in_flight || false
    const flightData = userPreviewData?.flight_data || null
    const isInCitadel = userPreviewData?.in_citadel || false

    return (
        <div className="dashboard-wrapper" data-city={userPreviewData?.city}>
            {/* ── Header Bar ─────────────────────────── */}
            <div className="header-bar">
                <h1 className="game-title">
                    Order <span className="accent">of</span> Elite
                </h1>

                <UserPreview
                    userPreviewData={userPreviewData}
                    isInFlight={isInFlight}
                    flightData={flightData}
                    isInCitadel={isInCitadel}
                />
            </div>

            {/* ── Center Layout ──────────────────────── */}
            <UserPreviewCtx.Provider value={{ userPreviewData, updateUserPreviewData }}>
                <div className="center-layout">
                    <ChatContainer messageUser={messageUser} />

                    <GameDash
                        tabComponents={tabComponents}
                        activeTab={activeTab}
                        isInFlight={isInFlight}
                        flightData={flightData}
                        isInCitadel={isInCitadel}
                        setUserProfileData={setUserProfileData}
                    />

                    <MenuItems
                        tabComponents={tabComponents}
                        activeTab={activeTab}
                        setActiveTab={setActiveTab}
                        isInFlight={isInFlight}
                    />
                </div>

                {showUserProfileModal && (
                    <UserProfileModal
                        userProfileData={userProfileData}
                        onClose={() => setShowUserProfileModal(false)}
                        onMessageClick={(messageUsername) => {
                            setMessageUser(messageUsername)
                            setShowUserProfileModal(false)
                        }}
                    />
                )}
            </UserPreviewCtx.Provider>
            <Footer />
        </div>
    )
}

function MenuItems({ tabComponents, activeTab, setActiveTab, isInFlight }) {
    return (
        <div className="menu-panel glass-panel">
            {Object.keys(tabComponents).map(tabKey => {
                return (
                    <button
                        className={`menu-btn ${activeTab === tabKey ? 'active' : ''}`}
                        key={tabKey}
                        onClick={() => setActiveTab(tabKey)}
                    >
                        {tabComponents[tabKey].label}
                    </button>
                )
            })}
        </div>
    )
}

function GameDash({
    tabComponents,
    activeTab,
    isInFlight,
    flightData,
    isInCitadel,
    setUserProfileData,
    setShowUserProfileModal
}) {
    const isBlockedByFlight = isInFlight && FLIGHT_BLOCKED_TABS.includes(activeTab)
    const isBlockedByCitadel = isInCitadel && CITADEL_BLOCKED_TABS.includes(activeTab)

    return (
        <div
            key={isBlockedByFlight ? 'flight-overlay'
                : isBlockedByCitadel ? 'citadel-overlay'
                : activeTab}
            className='central-panel glass-panel'
            style={{ position: 'relative' }}
        >
            {isBlockedByFlight ? (
                <FlightOverlay />
            ) : isBlockedByCitadel ? (
                <CitadelOverlay />
            ) : (
                React.createElement(tabComponents[activeTab].component,
                    tabComponents[activeTab].props)
            )}
        </div>
    )
}

const AnimatedMoney = ({ value }) => {
    const [displayValue, setDisplayValue] = useState(value)
    const [diffs, setDiffs] = useState([])
    const prevValueRef = useRef(value)

    useEffect(() => {
        if (value !== prevValueRef.current) {
            const diff = value - prevValueRef.current
            
            if (diff !== 0) {
                const newDiff = {
                    id: Date.now() + Math.random(),
                    amount: diff,
                }
                setDiffs(prev => [...prev, newDiff])
                
                setTimeout(() => {
                    setDiffs(prev => prev.filter(d => d.id !== newDiff.id))
                }, 2000)
            }

            const startValue = prevValueRef.current
            const endValue = value
            const duration = 300
            const startTime = performance.now()

            const animate = (currentTime) => {
                const elapsedTime = currentTime - startTime
                const progress = Math.min(elapsedTime / duration, 1)
                
                const currentVal = Math.round(startValue + (endValue - startValue) * progress)
                setDisplayValue(currentVal)

                if (progress < 1) {
                    requestAnimationFrame(animate)
                } else {
                    setDisplayValue(endValue)
                }
            }

            requestAnimationFrame(animate)
            prevValueRef.current = value
        }
    }, [value])

    return (
        <span className="animated-money-container">
            <span className="money-diffs-container">
                {diffs.map(d => (
                    <span 
                        key={d.id} 
                        className={`money-diff ${d.amount >= 0 ? 'diff-positive' : 'diff-negative'}`}
                    >
                        {d.amount >= 0 ? '+' : '-'} {formatMoney(Math.abs(d.amount))}
                    </span>
                ))}
            </span>
            <span>{formatMoney(displayValue)}</span>
        </span>
    )
}


/**
 * AnimatedSkill — shows the effective skill value with a floating +N diff
 * whenever the value changes (e.g. after training or equipping an item).
 */
const AnimatedSkill = ({ value }) => {
    const [displayValue, setDisplayValue] = useState(value)
    const [diffs, setDiffs] = useState([])
    const prevValueRef = useRef(value)

    useEffect(() => {
        if (value !== prevValueRef.current) {
            const diff = value - prevValueRef.current
            if (diff !== 0) {
                const newDiff = { id: Date.now() + Math.random(), amount: diff }
                setDiffs(prev => [...prev, newDiff])
                setTimeout(() => {
                    setDiffs(prev => prev.filter(d => d.id !== newDiff.id))
                }, 2000)
            }

            const startValue = prevValueRef.current
            const endValue = value
            const duration = 300
            const startTime = performance.now()
            const animate = (currentTime) => {
                const elapsed = currentTime - startTime
                const progress = Math.min(elapsed / duration, 1)
                setDisplayValue(Math.round(startValue + (endValue - startValue) * progress))
                if (progress < 1) requestAnimationFrame(animate)
                else setDisplayValue(endValue)
            }
            requestAnimationFrame(animate)
            prevValueRef.current = value
        }
    }, [value])

    return (
        <span className="animated-skill-container">
            <span className="skill-diffs-container">
                {diffs.map(d => (
                    <span
                        key={d.id}
                        className={`skill-diff ${d.amount >= 0 ? 'diff-positive' : 'diff-negative'}`}
                    >
                        {d.amount >= 0 ? '+' : ''}{d.amount}
                    </span>
                ))}
            </span>
            <span>{displayValue}</span>
        </span>
    )
}


/**
 * SkillTooltip — glass card showing base pts, per-source multipliers, and final total.
 */
function SkillTooltip({ skillKey, basePoints, effectivePoints, multiplier, sources }) {
    const SOURCE_LABELS = {
        citadel: 'Citadel',
        house:   'House',
        car:     'Car',
        gun:     'Gun',
    }

    const relevantSources = Object.entries(sources || {}).filter(([, data]) => {
        const v = data[skillKey]
        return v && v !== 1.0
    })

    return (
        <div className="skill-tooltip">
            <div className="skill-tooltip-title">{skillKey.charAt(0).toUpperCase() + skillKey.slice(1)}</div>
            <div className="skill-tooltip-row">
                <span className="skill-tooltip-label">Base</span>
                <span className="skill-tooltip-value">{basePoints}</span>
            </div>
            {relevantSources.map(([source, data]) => {
                const mx = data[skillKey]
                const label = data.name || SOURCE_LABELS[source] || source
                return (
                    <div className="skill-tooltip-row skill-tooltip-multiplier" key={source}>
                        <span className="skill-tooltip-label">{label}</span>
                        <span className="skill-tooltip-value skill-tooltip-mult-value">{mx}x</span>
                    </div>
                )
            })}
            <div className="skill-tooltip-divider" />
            <div className="skill-tooltip-row skill-tooltip-total">
                <span className="skill-tooltip-label">Total</span>
                <span className="skill-tooltip-value">{effectivePoints}</span>
            </div>
        </div>
    )
}


/**
 * Milliseconds until the next Elite Coins reset (Monday 00:00 UTC).
 */
function msUntilNextEliteCoinReset() {
    const now = new Date()
    const day = now.getUTCDay() // Sun=0 ... Mon=1 ... Sat=6
    let daysUntilMonday = (1 - day + 7) % 7
    if (daysUntilMonday === 0) daysUntilMonday = 7
    const next = Date.UTC(
        now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + daysUntilMonday, 0, 0, 0
    )
    return Math.max(0, next - now.getTime())
}

function formatEliteCoinCountdown(ms) {
    const totalMinutes = Math.floor(ms / 60000)
    const days = Math.floor(totalMinutes / 1440)
    const hours = Math.floor((totalMinutes % 1440) / 60)
    const minutes = totalMinutes % 60
    if (days > 0) return `${days}d ${hours}h`
    if (hours > 0) return `${hours}h ${minutes}m`
    return `${minutes}m`
}

/**
 * EliteCoinTooltip — glass card explaining the weekly reset, shared
 * visual language with SkillTooltip (same CSS classes).
 */
function EliteCoinTooltip({ eliteCoins }) {
    const [countdown, setCountdown] = useState(msUntilNextEliteCoinReset())

    useEffect(() => {
        const interval = setInterval(() => setCountdown(msUntilNextEliteCoinReset()), 30000)
        return () => clearInterval(interval)
    }, [])

    return (
        <div className="skill-tooltip">
            <div className="skill-tooltip-title">Elite Coins</div>
            <div className="skill-tooltip-row">
                <span className="skill-tooltip-label">Balance</span>
                <span className="skill-tooltip-value">{eliteCoins}</span>
            </div>
            <div className="skill-tooltip-divider" />
            <div className="skill-tooltip-row">
                <span className="skill-tooltip-label">Resets to 10 every Monday, 00:00 UTC</span>
            </div>
            <div className="skill-tooltip-row skill-tooltip-total">
                <span className="skill-tooltip-label">Next reset in</span>
                <span className="skill-tooltip-value">{formatEliteCoinCountdown(countdown)}</span>
            </div>
        </div>
    )
}


/**
 * FlightRouteIndicator
 * Shows: OriginCity ...●...●...● DestinationCity
 * with a progress-based animated dots line and an ETA label on top (hours/minutes, no seconds).
 */
function FlightRouteIndicator({ flightData }) {
    const [etaLabel, setEtaLabel] = useState('')
    const [progress, setProgress] = useState(0)

    useEffect(() => {
        const tick = () => {
            const now = Math.floor(Date.now() / 1000)
            const total = flightData.arrival_time - flightData.departed_at
            const elapsed = now - flightData.departed_at
            const remaining = Math.max(0, flightData.arrival_time - now)

            // Progress 0→1
            const pct = total > 0 ? Math.min(1, elapsed / total) : 0
            setProgress(pct)

            // ETA label (no seconds)
            const totalMins = Math.floor(remaining / 60)
            const h = Math.floor(totalMins / 60)
            const m = totalMins % 60
            if (remaining <= 0) {
                setEtaLabel('Arriving...')
            } else if (h > 0) {
                setEtaLabel(`${h}h ${m}m`)
            } else {
                setEtaLabel(`${m}m`)
            }
        }

        tick()
        const interval = setInterval(tick, 10000) // update every 10s (no seconds shown)
        return () => clearInterval(interval)
    }, [flightData])

    // 7 dots total — light up based on progress
    const DOT_COUNT = 7
    const litDots = Math.round(progress * DOT_COUNT)

    return (
        <div className="flight-route-indicator">
            <div className="flight-route-eta">{etaLabel}</div>
            <div className="flight-route-track">
                <span className="flight-route-city flight-route-city--origin">
                    {flightData.origin_city}
                </span>
                <div className="flight-route-dots">
                    {Array.from({ length: DOT_COUNT }).map((_, i) => (
                        <span
                            key={i}
                            className={`flight-route-dot ${i < litDots ? 'flight-route-dot--lit' : ''}`}
                        />
                    ))}
                </div>
                <span className="flight-route-city flight-route-city--dest">
                    {flightData.destination_city}
                </span>
            </div>
        </div>
    )
}


function healthTier(health) {
    if (health <= 50) return 'low'
    if (health <= 99) return 'mid'
    return 'full'
}

const UserPreview = memo(({ userPreviewData, isInFlight, flightData, isInCitadel }) => {
    const [tooltipSkill, setTooltipSkill] = useState(null)
    const [showEliteCoinTooltip, setShowEliteCoinTooltip] = useState(false)

    const SKILL_DEFS = [
        { key: 'attack',  icon: '⚔',  pointsKey: 'attack_points',  baseKey: 'base_attack_points',  multKey: 'attack_multiplier' },
        { key: 'defense', icon: '🛡', pointsKey: 'defense_points', baseKey: 'base_defense_points', multKey: 'defense_multiplier' },
        { key: 'driving', icon: '🏎', pointsKey: 'driving_points', baseKey: 'base_driving_points', multKey: 'driving_multiplier' },
    ]

    return (
        <div className="user-preview-bar glass-panel">
            {userPreviewData ? (
                <>
                    <div className="user-preview-top">
                        <span className="user-preview-username">
                            {userPreviewData.username}
                            {userPreviewData.is_premium && (
                                <span className="user-preview-premium-mark" title="Member of standing">✦</span>
                            )}
                            {userPreviewData.persona_non_grata && (
                                <span className="user-preview-png-badge" title="Persona non grata">
                                    PERSONA NON GRATA
                                </span>
                            )}
                        </span>

                        {isInFlight && flightData ? (
                            <FlightRouteIndicator flightData={flightData} />
                        ) : (
                            <span className="user-preview-city">
                                {userPreviewData.city.toUpperCase()}
                                {isInCitadel && (
                                    <span className="user-preview-citadel-badge">🏛 CITADEL</span>
                                )}
                            </span>
                        )}

                        <span className="user-preview-resources">
                            <span className={`user-preview-hp user-preview-hp--${healthTier(userPreviewData.health)}`}>
                                <span className="up-stat-label">HP</span> {userPreviewData.health}%
                            </span>

                            <span
                                className="user-preview-elite-coins"
                                onMouseEnter={() => setShowEliteCoinTooltip(true)}
                                onMouseLeave={() => setShowEliteCoinTooltip(false)}
                            >
                                🪙 <AnimatedSkill value={userPreviewData.elite_coins} />
                                {showEliteCoinTooltip && (
                                    <EliteCoinTooltip eliteCoins={userPreviewData.elite_coins} />
                                )}
                            </span>

                            <span className="user-preview-money"><AnimatedMoney value={userPreviewData.money_cash} /></span>
                        </span>
                    </div>

                    <div className="progress-bar-track">
                        <div
                            className="progress-bar-fill"
                            style={{ width: `${Math.floor(userPreviewData.rank_progress)}%` }}
                        />
                    </div>

                    <div className="user-preview-stats" style={{ marginTop: '6px' }}>
                        <span className="up-stat-rank">
                            <span className="up-stat-label">RANK</span>
                            <span className="up-stat-value">{userPreviewData.rank}</span>
                            <span className="up-stat-progress">({Math.floor(userPreviewData.rank_progress)}%)</span>
                        </span>
                        <span className="up-stat-sep">|</span>

                        {SKILL_DEFS.map(({ key, icon, pointsKey, baseKey, multKey }) => {
                            const effective = userPreviewData[pointsKey]
                            const base = userPreviewData[baseKey] ?? effective
                            const multiplier = userPreviewData[multKey] ?? 1.0
                            const isOpen = tooltipSkill === key

                            return (
                                <span
                                    key={key}
                                    className="up-skill-stat"
                                    onMouseEnter={() => setTooltipSkill(key)}
                                    onMouseLeave={() => setTooltipSkill(null)}
                                >
                                    <span className="up-skill-icon">{icon}</span>
                                    <span className="up-skill-value">
                                        <AnimatedSkill value={effective} />
                                    </span>
                                    {isOpen && (
                                        <SkillTooltip
                                            skillKey={key}
                                            basePoints={base}
                                            effectivePoints={effective}
                                            multiplier={multiplier}
                                            sources={userPreviewData.skill_multipliers || {}}
                                        />
                                    )}
                                </span>
                            )
                        })}
                    </div>
                </>
            ) : (
                <p className="loading-text">LOADING...</p>
            )}
        </div>
    )
})



function DashboardTab() {
    return (
        <div className="dashboard-welcome">
            <h2>WELCOME, OPERATIVE</h2>
            <p>
                The Citadel awaits your next move.
                Select a section from the menu to begin operations.
            </p>
        </div>
    )
}

export default Dashboard
