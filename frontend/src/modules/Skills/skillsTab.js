import React, { useState, useEffect, useContext } from 'react'
import { request, formatSeconds, formatMoney, secondsRemaining } from 'modules/Base'
import { UserPreviewCtx } from 'modules/Dashboard'

const SKILL_CONFIG = {
    attack: {
        label: 'Attack',
        icon: '⚔',
        description: 'Increases your chances of a successful backfire and assassination against other players and NPCs during missions.',
    },
    defense: {
        label: 'Defense',
        icon: '🛡',
        description: 'Improves your chances of survival when other players make an assassination attempt on your life.',
    },
    driving: {
        label: 'Driving',
        icon: '🏎',
        description: 'Vastly improves mission outcomes when you\'re behind the wheel, and slightly tips assassination odds in your favor.',
    },
}

const SKILL_NAMES = ['attack', 'defense', 'driving']

function TrainingPanel({ title, tier, selected, onSelect, cost, points, cooldownDuration, cooldownRemaining, isAvailable, currentStats, onTrain }) {
    const isCoolingDown = cooldownRemaining > 0
    const config = SKILL_CONFIG[selected]

    return (
        <div className={`training-panel ${tier}`}>
            <div className="training-panel-header">
                <h3>{title}</h3>
                <div className="training-panel-meta">
                    <span className="training-cost">{cost === 0 ? 'Free' : formatMoney(cost)}</span>
                    <span className="training-divider">·</span>
                    <span className="training-points">+{points} pt{points !== 1 ? 's' : ''}</span>
                    <span className="training-divider">·</span>
                    <span className="training-cooldown-info">
                        <span className="training-clock">🕐</span>
                        {formatSeconds(cooldownDuration)}
                    </span>
                </div>
            </div>

            <div className="skill-selector">
                {SKILL_NAMES.map(key => (
                    <button
                        key={key}
                        type="button"
                        className={`skill-select-btn ${tier} ${selected === key ? 'active' : ''}`}
                        onClick={() => onSelect(key)}
                    >
                        <span className="skill-select-icon">{SKILL_CONFIG[key].icon}</span>
                        <span className="skill-select-label">{SKILL_CONFIG[key].label}</span>
                        <span className="skill-select-value">{currentStats?.[`${key}_points`] ?? '—'}</span>
                    </button>
                ))}
            </div>

            <p className="skill-description">{config.description}</p>

            <button
                className={`btn-train-main ${tier} ${isCoolingDown ? 'cooldown' : ''}`}
                disabled={!isAvailable}
                onClick={onTrain}
            >
                {isCoolingDown ? formatSeconds(cooldownRemaining) : `Train ${config.label}`}
            </button>
        </div>
    )
}

function SkillsTab() {
    const [skillsData, setSkillsData] = useState(null)
    const [freeSkill, setFreeSkill] = useState('attack')
    const [proSkill, setProSkill] = useState('attack')
    const { userPreviewData, updateUserPreviewData } = useContext(UserPreviewCtx)

    useEffect(() => {
        request({
            'url': 'users/get_skills_tab_data',
            'method': 'POST',
        })
        .then(response => {
            setSkillsData({
                    ...response.data,

                    attack_free_available: secondsRemaining(response.data.attack_free_cd) <= 0,
                    attack_pro_available: secondsRemaining(response.data.attack_pro_cd) <= 0,
                    defense_free_available: secondsRemaining(response.data.defense_free_cd) <= 0,
                    defense_pro_available: secondsRemaining(response.data.defense_pro_cd) <= 0,
                    driving_free_available: secondsRemaining(response.data.driving_free_cd) <= 0,
                    driving_pro_available: secondsRemaining(response.data.driving_pro_cd) <= 0,

                    attack_free_cd: secondsRemaining(response.data.attack_free_cd),
                    attack_pro_cd: secondsRemaining(response.data.attack_pro_cd),
                    defense_free_cd: secondsRemaining(response.data.defense_free_cd),
                    defense_pro_cd: secondsRemaining(response.data.defense_pro_cd),
                    driving_free_cd: secondsRemaining(response.data.driving_free_cd),
                    driving_pro_cd: secondsRemaining(response.data.driving_pro_cd),
            })
        })
        .catch(error => {
            console.error("Error getting skills tab data: ", error)
        })
    }, [])

    useEffect(() => {
        if (!skillsData) return

        const skills = ['attack_free',
            'attack_pro',
            'defense_free',
            'defense_pro',
            'driving_free',
            'driving_pro']

        const interval = setInterval(() => {

            skills.forEach(skill => {
                const cd = skillsData[`${skill}_cd`]
                if (cd > 0) {
                    setSkillsData(data => {
                        return {
                            ...data,
                            [`${skill}_cd`]: cd - 1,
                            [`${skill}_available`]: cd - 1 <= 0,
                        }
                    })
                }
            })
        }, 1000)

        return () => clearInterval(interval);
    }, [skillsData])

    const startPractice = (skillName) => {
        request({
            'url': `users/start_skill_practice/${skillName}`,
            'method': 'POST',
        })
        .then(response => {
            updateUserPreviewData()

            setSkillsData(data => {
                const suffix = skillName.endsWith('_free') ? '_free' : '_pro'
                const cdSecs = secondsRemaining(response.data.cd_remaining)
                return {
                    ...data,
                    [`attack${suffix}_cd`]: cdSecs,
                    [`attack${suffix}_available`]: false,
                    [`defense${suffix}_cd`]: cdSecs,
                    [`defense${suffix}_available`]: false,
                    [`driving${suffix}_cd`]: cdSecs,
                    [`driving${suffix}_available`]: false,
                }
            })
        })
        .catch(error => {
            console.error("Error starting practice:", error)
        })
    }

    if (skillsData === null) {
        return <div className="loading-text">LOADING SKILLS...</div>
    }

    return (
        <div className="skills-container">
            <p className="skills-intro-text">
                Training sharpens one discipline at a time. Free and professional instructors each accept a single assignment before they need to recover — choose carefully.
            </p>

            <TrainingPanel
                title="Free Training"
                tier="free"
                selected={freeSkill}
                onSelect={setFreeSkill}
                cost={0}
                points={skillsData.free_points}
                cooldownDuration={skillsData.free_cooldown}
                cooldownRemaining={skillsData[`${freeSkill}_free_cd`]}
                isAvailable={skillsData[`${freeSkill}_free_available`]}
                currentStats={userPreviewData}
                onTrain={() => startPractice(`${freeSkill}_free`)}
            />

            <TrainingPanel
                title="Professional Training"
                tier="pro"
                selected={proSkill}
                onSelect={setProSkill}
                cost={skillsData[`${proSkill}_pro_price`]}
                points={skillsData.pro_points}
                cooldownDuration={skillsData.pro_cooldown}
                cooldownRemaining={skillsData[`${proSkill}_pro_cd`]}
                isAvailable={skillsData[`${proSkill}_pro_available`]}
                currentStats={userPreviewData}
                onTrain={() => startPractice(`${proSkill}_pro`)}
            />
        </div>
    )
}

export default SkillsTab
