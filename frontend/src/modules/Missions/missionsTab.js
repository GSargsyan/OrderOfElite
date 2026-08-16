import React, { useState, useEffect, useContext, useCallback } from 'react'
import { request, formatSeconds, formatMoney, secondsRemaining } from 'modules/Base'
import { UserPreviewCtx } from 'modules/Dashboard'

const ROLE_LABELS = { initiator: 'Initiator', driver: 'Driver', assassin: 'Assassin' }

function roleLabel(role) {
    return ROLE_LABELS[role] || role
}

function MissionsTab() {
    console.log('MissionsTab rendered')
    const [missionsData, setMissionsData] = useState(null)
    const [isStakeoutAvailable, setIsStakeoutAvailable] = useState(false)
    const [isReconOpAvailable, setIsReconOpAvailable] = useState(false)
    const [stakeoutCdRemaining, setStakeoutCdRemaining] = useState(0)
    const [reconOpCdRemaining, setReconOpCdRemaining] = useState(0)
    const [isStakeoutAllowed, setIsStakeoutAllowed] = useState(false)
    const [isReconOpAllowed, setIsReconOpAllowed] = useState(false)

    const { updateUserPreviewData } = useContext(UserPreviewCtx)

    const loadMissionsData = useCallback(() => {
        request({
            'url': 'missions/get_missions_tab_data',
            'method': 'POST',
        })
            .then(response => {
                console.log('missions/get_missions_tab_data')
                setMissionsData(response.data)

                setIsStakeoutAllowed(response.data.stakeout.allowed)
                setIsReconOpAllowed(response.data.recon_op.allowed)

                setStakeoutCdRemaining(secondsRemaining(response.data.stakeout.cd_remaining))
                setReconOpCdRemaining(secondsRemaining(response.data.recon_op.cd_remaining))

                setIsStakeoutAvailable(response.data.stakeout.allowed &&
                    secondsRemaining(response.data.stakeout.cd_remaining) <= 0)

                setIsReconOpAvailable(response.data.recon_op.allowed &&
                    secondsRemaining(response.data.recon_op.cd_remaining) <= 0)
            })
            .catch(error => {
                console.error("Error getting missions tab data: ", error)
            })
    }, [])

    useEffect(() => {
        loadMissionsData()
    }, [loadMissionsData])

    useEffect(() => {
        if (!missionsData) return

        const interval = setInterval(() => {
            if (stakeoutCdRemaining > 0) {
                setStakeoutCdRemaining(cd => {
                    setIsStakeoutAvailable(isStakeoutAllowed && cd - 1 <= 0)
                    return cd - 1
                })
            }

            if (reconOpCdRemaining > 0) {
                setReconOpCdRemaining(cd => cd - 1)
            }
        }, 1000)

        return () => clearInterval(interval);
    }, [stakeoutCdRemaining, reconOpCdRemaining, isReconOpAllowed, isStakeoutAllowed, missionsData])

    const startMission = (missionType) => {
        console.log(`missions/start/${missionType}`)
        request({
            'url': `missions/start/${missionType}`,
            'method': 'POST',
        })
            .then(response => {
                updateUserPreviewData()

                if (missionType === 'stakeout') {
                    setIsStakeoutAvailable(false)
                    setStakeoutCdRemaining(secondsRemaining(response.data.cd_remaining))
                } else if (missionType === 'recon_op') {
                    setIsReconOpAvailable(false)
                    setReconOpCdRemaining(secondsRemaining(response.data.cd_remaining))
                }
            })
            .catch(error => {
                console.error("Error starting mission:", error)
            })
    }

    if (missionsData === null) {
        return <div className="loading-text">LOADING MISSIONS...</div>
    }

    return (
        <div className="missions-grid">
            {/* Stakeout Mission Card */}
            <div className="mission-card">
                <div className="mission-card-header">
                    <h3>Stakeout</h3>
                    {stakeoutCdRemaining > 0 && (
                        <div className="mission-timer">
                            <span className="timer-icon">⏱</span>
                            {formatSeconds(stakeoutCdRemaining)}
                        </div>
                    )}
                </div>
                <p>
                    Grants a cash reward and experience on completion.
                </p>
                <button
                    className="btn-mission-start"
                    disabled={!isStakeoutAvailable}
                    onClick={() => startMission('stakeout')}
                >
                    Start
                </button>
            </div>

            {/* Recon Op Mission Card */}
            <div className="mission-card">
                <div className="mission-card-header">
                    <h3>Recon Op</h3>
                    {reconOpCdRemaining > 0 && (
                        <div className="mission-timer">
                            <span className="timer-icon">⏱</span>
                            {formatSeconds(reconOpCdRemaining)}
                        </div>
                    )}
                </div>
                <p>
                    Grants a larger cash reward and experience on completion.
                    Unlocks at Rank 2.
                </p>
                <button
                    className="btn-mission-start"
                    disabled={!isReconOpAvailable}
                    onClick={() => startMission('recon_op')}
                >
                    Start
                </button>
            </div>

            <PartyMissionCard
                missionType="exfiltration"
                title="Exfiltration"
                unlockNote="Unlocks at Rank 5."
                description="A two-player mission. An Initiator invites a Driver located in
                    their city. Once underway, the operation takes 5 minutes to conclude;
                    the Driver's car is consumed on start. The reward is paid to the
                    Initiator; both participants earn experience."
                data={missionsData.exfiltration}
                reload={loadMissionsData}
            />

            <PartyMissionCard
                missionType="hvt"
                title="High-Profile Target Operation"
                unlockNote="Unlocks at Rank 8."
                description="A four-player mission. An Initiator invites a Driver and two
                    Assassins located in their city. Once underway, the operation takes
                    5 minutes to conclude; each participant's chosen gear is consumed on
                    start. The reward is paid to the Initiator; every participant earns
                    experience."
                data={missionsData.hvt}
                reload={loadMissionsData}
            />
        </div>
    )
}

function PartyMissionCard({ missionType, title, description, unlockNote, data, reload }) {
    const [now, setNow] = useState(() => Math.floor(Date.now() / 1000))
    const [inviteUsernames, setInviteUsernames] = useState({})
    const [selectedItem, setSelectedItem] = useState('')
    const [error, setError] = useState(null)

    useEffect(() => {
        const interval = setInterval(() => setNow(Math.floor(Date.now() / 1000)), 1000)
        return () => clearInterval(interval)
    }, [])

    // Poll while an operation is underway so the Claim button appears
    // without the player needing to leave and come back to this tab.
    const missionStatus = data?.mission?.status
    useEffect(() => {
        if (missionStatus !== 'in_progress') return
        const interval = setInterval(reload, 10000)
        return () => clearInterval(interval)
    }, [missionStatus, reload])

    if (!data) return null

    const cdRemaining = secondsRemaining(data.cd_remaining)
    const mission = data.mission

    const action = (actionName, payload = {}) => {
        setError(null)
        request({
            url: `missions/party/${missionType}/${actionName}`,
            method: 'POST',
            data: payload,
        })
            .then(() => {
                setSelectedItem('')
                reload()
            })
            .catch(err => {
                setError(err.response?.data?.message || 'Something went wrong')
                reload()
            })
    }

    const claim = () => {
        setError(null)
        request({
            url: `missions/party/${missionType}/claim`,
            method: 'POST',
            data: { mission_id: mission.id },
        })
            .then(res => {
                alert(res.data.reward
                    ? `${title} complete. You earned $${res.data.reward.toLocaleString('en-US')} and ${res.data.exp_reward} EXP.`
                    : `${title} complete. You earned ${res.data.exp_reward} EXP.`)
                reload()
            })
            .catch(err => {
                setError(err.response?.data?.message || 'Something went wrong')
                reload()
            })
    }

    const sendInvite = (role) => {
        const username = (inviteUsernames[role] || '').trim()
        if (!username) return
        action('invite', { role, username })
        setInviteUsernames(prev => ({ ...prev, [role]: '' }))
    }

    if (!data.allowed) {
        return (
            <div className="mission-card mission-card-exfiltration">
                <div className="mission-card-header"><h3>{title}</h3></div>
                <p>{description}</p>
                <p className="exfiltration-note">{unlockNote}</p>
            </div>
        )
    }

    const renderIdle = () => {
        if (cdRemaining > 0) {
            return <p className="exfiltration-note">{title} is on cooldown.</p>
        }

        const openRoles = data.roles || {}

        return (
            <div className="exfiltration-sections">
                <div className="exfiltration-section">
                    <h4>Host {title}</h4>
                    <p className="exfiltration-note">
                        Invite participants located in your city. Everyone must be
                        ready before the operation can start.
                    </p>
                    {Object.keys(openRoles).map(role => (
                        <div className="exfiltration-invite-row" key={role}>
                            <input
                                className="exfiltration-input"
                                type="text"
                                placeholder={`${roleLabel(role)}'s name`}
                                autoComplete="new-password"
                                value={inviteUsernames[role] || ''}
                                onChange={e => setInviteUsernames(prev => ({ ...prev, [role]: e.target.value }))}
                                onKeyDown={e => { if (e.key === 'Enter') sendInvite(role) }}
                            />
                            <button
                                className="btn-mission-start"
                                disabled={!(inviteUsernames[role] || '').trim()}
                                onClick={() => sendInvite(role)}
                            >
                                Invite {roleLabel(role)}
                            </button>
                        </div>
                    ))}
                </div>

                <div className="exfiltration-section">
                    <h4>Invitations</h4>
                    {data.invitations.length === 0 ? (
                        <p className="exfiltration-note">No invitations at the moment.</p>
                    ) : (
                        data.invitations.map(inv => (
                            <div className="exfiltration-invitation-row" key={inv.id}>
                                <span className="exfiltration-invitation-name">
                                    {inv.initiator} — {roleLabel(inv.role)}
                                </span>
                                <div className="exfiltration-invitation-actions">
                                    <button
                                        className="btn-exfiltration-small"
                                        onClick={() => action('accept', { mission_id: inv.mission_id })}
                                    >
                                        Accept
                                    </button>
                                    <button
                                        className="btn-exfiltration-small btn-exfiltration-danger"
                                        onClick={() => action('reject', { mission_id: inv.mission_id })}
                                    >
                                        Reject
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        )
    }

    const renderRoster = () => (
        <div className="exfiltration-roster">
            {mission.participants.map(p => (
                <div className="exfiltration-roster-row" key={p.username}>
                    <span className="exfiltration-label">{roleLabel(p.role)}</span>
                    <span>
                        {p.username}{p.is_me && ' (you)'}
                        {p.item_name && ` — ${p.item_name}`}
                        {p.role !== 'initiator' && (
                            <span className={p.invite_status === 'ready' ? ' exfiltration-highlight' : ''}>
                                {' '}({p.invite_status})
                            </span>
                        )}
                    </span>
                </div>
            ))}
        </div>
    )

    const renderLobby = () => {
        const openRoles = mission.open_roles || {}
        const myItems = mission.my_item_type === 'car' ? data.cars : data.guns

        return (
            <div className="exfiltration-setup">
                {renderRoster()}

                {mission.my_role !== 'initiator' && mission.my_invite_status === 'accepted' && (
                    (myItems || []).length === 0 ? (
                        <p className="exfiltration-note">
                            You don't own a {mission.my_item_type} in this city. Get one to join this operation.
                        </p>
                    ) : (
                        <div className="exfiltration-driver-panel">
                            <p className="exfiltration-note">
                                The {mission.my_item_type} you choose will be consumed when the operation starts.
                            </p>
                            <div className="exfiltration-invite-row">
                                <select
                                    className="exfiltration-input"
                                    value={selectedItem}
                                    onChange={e => setSelectedItem(e.target.value)}
                                >
                                    <option value="">Choose a {mission.my_item_type}…</option>
                                    {myItems.map(item => (
                                        <option key={item.key} value={item.key}>{item.name}</option>
                                    ))}
                                </select>
                                <button
                                    className="btn-mission-start"
                                    disabled={!selectedItem}
                                    onClick={() => action('ready', { mission_id: mission.id, item: selectedItem })}
                                >
                                    Ready
                                </button>
                            </div>
                        </div>
                    )
                )}

                {mission.my_role !== 'initiator' && mission.my_invite_status === 'ready' && (
                    <p className="exfiltration-note">
                        You are ready. Waiting for the Initiator to start the operation.
                    </p>
                )}

                {Object.keys(openRoles).length > 0 && (
                    <p className="exfiltration-note">
                        Open roles: {Object.entries(openRoles).map(([role, count]) =>
                            `${count} × ${roleLabel(role)}`).join(', ')}
                    </p>
                )}

                <div className="exfiltration-actions">
                    {mission.my_role === 'initiator' && (
                        <button
                            className="btn-mission-start"
                            disabled={Object.keys(openRoles).length > 0 ||
                                mission.participants.some(p => p.role !== 'initiator' && p.invite_status !== 'ready')}
                            onClick={() => action('start', { mission_id: mission.id })}
                        >
                            Start
                        </button>
                    )}
                    {mission.my_role !== 'initiator' && mission.my_invite_status === 'ready' && (
                        <button
                            className="btn-exfiltration-small"
                            onClick={() => action('unready', { mission_id: mission.id })}
                        >
                            Not Ready
                        </button>
                    )}
                    <button
                        className="btn-exfiltration-small btn-exfiltration-danger"
                        onClick={() => action('cancel', { mission_id: mission.id })}
                    >
                        Abort
                    </button>
                </div>
            </div>
        )
    }

    const renderInProgress = () => {
        const remaining = Math.max(0, Math.round(mission.resolves_at - now))

        return (
            <div className="exfiltration-setup">
                {renderRoster()}
                <p className="exfiltration-note">
                    Operation in progress — resolving in {formatSeconds(remaining)}. During this
                    window, an assassination attempt against a fellow participant does not
                    require a prior Search.
                </p>
            </div>
        )
    }

    const renderResolved = () => (
        <div className="exfiltration-setup">
            {renderRoster()}
            {mission.my_claimed ? (
                <p className="exfiltration-note">
                    You have claimed your share. Waiting for the rest of the team.
                </p>
            ) : (
                <>
                    <p className="exfiltration-note">
                        Operation complete.{' '}
                        {mission.my_role === 'initiator'
                            ? `Ready to claim: ${formatMoney(mission.reward)} and ${mission.exp_reward} EXP.`
                            : `Ready to claim: ${mission.exp_reward} EXP.`}
                    </p>
                    <button className="btn-mission-start" onClick={claim}>
                        Claim
                    </button>
                </>
            )}
        </div>
    )

    const renderBody = () => {
        if (!mission) return renderIdle()
        if (mission.status === 'in_progress') return renderInProgress()
        if (mission.status === 'resolved') return renderResolved()
        return renderLobby()
    }

    return (
        <div className="mission-card mission-card-exfiltration">
            <div className="mission-card-header">
                <h3>{title}</h3>
                {cdRemaining > 0 && !mission && (
                    <div className="mission-timer">
                        <span className="timer-icon">⏱</span>
                        {formatSeconds(cdRemaining)}
                    </div>
                )}
            </div>
            <p>{description}</p>
            {error && <div className="profile-error">{error}</div>}
            {renderBody()}
        </div>
    )
}

export default MissionsTab
