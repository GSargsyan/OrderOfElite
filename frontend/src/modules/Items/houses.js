import React, { useState, useEffect, useContext } from 'react'
import { request, formatMoney } from 'modules/Base'
import { UserPreviewCtx } from 'modules/Dashboard'

import luxuryCondo from 'assets/pictures/houses/luxury_condo.png'
import mansionEstate from 'assets/pictures/houses/mansion_estate.png'
import studioApartment from 'assets/pictures/houses/studio_apartment.png'

const HOUSE_IMAGES = {
    luxury_condo: luxuryCondo,
    mansion_estate: mansionEstate,
    studio_apartment: studioApartment,
}

function Houses() {
    const [houses, setHouses] = useState(null)
    const { updateUserPreviewData } = useContext(UserPreviewCtx)

    useEffect(() => {
        getHousesData()
    }, [])

    const getHousesData = () => {
        request({ url: 'items/get_user_houses', method: 'POST' })
            .then(response => setHouses(response.data))
            .catch(error => console.error('Error getting houses data:', error))
    }

    const buyHouse = (houseKey) => {
        request({ url: 'items/buy_house', method: 'POST', data: { house_name: houseKey } })
            .then(() => {
                alert('House purchased successfully')
                updateUserPreviewData()
                getHousesData()
            })
            .catch(error => alert(error.response.data.message))
    }

    const sellHouse = (houseKey) => {
        if (!window.confirm('Are you sure you want to sell this house?')) return
        request({ url: 'items/sell_house', method: 'POST', data: { house_name: houseKey } })
            .then(() => {
                alert('House sold successfully')
                updateUserPreviewData()
                getHousesData()
            })
            .catch(error => alert(error.response.data.message))
    }

    const equipHouse = (houseKey) => {
        request({ url: 'items/equip_house', method: 'POST', data: { house_name: houseKey } })
            .then(() => {
                updateUserPreviewData()
                getHousesData()
            })
            .catch(error => alert(error.response.data.message))
    }

    const unequipHouse = () => {
        request({ url: 'items/unequip_house', method: 'POST' })
            .then(() => {
                updateUserPreviewData()
                getHousesData()
            })
            .catch(error => alert(error.response.data.message))
    }

    if (houses === null) {
        return <div className="loading-text">LOADING...</div>
    }

    return (
        <div>
            {Object.keys(houses).map(houseKey => {
                const house = houses[houseKey]
                const owned = house.owns_in_current_city
                const equipped = house.is_equipped

                return (
                    <div className={`item-card ${equipped ? 'item-card--equipped' : ''}`} key={houseKey}>
                        <img className="item-image" src={HOUSE_IMAGES[houseKey]} alt={house.name} />
                        <div className="item-info">
                            <h2>
                                {house.name}
                                {equipped && <span className="item-equipped-badge">EQUIPPED</span>}
                            </h2>
                            <div className="item-owned-cities">
                                <span>Owned in cities: </span>
                                {house.owns_in_cities.length === 0 ? (
                                    <span>None</span>
                                ) : (
                                    <span>{house.owns_in_cities.join(', ')}</span>
                                )}
                            </div>
                            <p>Price: <strong className="item-price-value">{formatMoney(house.price)}</strong></p>
                            <p>Defense: {house.defense_multiplier}x</p>
                            <p>
                                Garage: <strong>{house.garage_capacity}</strong> car{house.garage_capacity !== 1 ? 's' : ''}
                            </p>
                            <p className="item-maintenance-cost">
                                Maintenance: <strong>{formatMoney(house.maintenance_cost)}</strong>
                                <span className="item-cost-period"> / day</span>
                            </p>

                            <div className="item-action-row">
                                {!owned ? (
                                    <button className="btn-buy" onClick={() => buyHouse(houseKey)}>
                                        Buy
                                    </button>
                                ) : equipped ? (
                                    <>
                                        <button className="btn-unequip" onClick={() => unequipHouse()}>
                                            Unequip
                                        </button>
                                        <button className="btn-sell" onClick={() => sellHouse(houseKey)}>
                                            Sell
                                        </button>
                                    </>
                                ) : (
                                    <>
                                        <button className="btn-equip" onClick={() => equipHouse(houseKey)}>
                                            Equip
                                        </button>
                                        <button className="btn-sell" onClick={() => sellHouse(houseKey)}>
                                            Sell
                                        </button>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                )
            })}
        </div>
    )
}

export default Houses