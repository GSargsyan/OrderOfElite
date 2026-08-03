import React, { useState } from 'react'

function AssassinationTab() {
    const [eliteName, setEliteName] = useState('')
    const [operationalBudget, setOperationalBudget] = useState('')

    return (
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
    )
}

export default AssassinationTab
