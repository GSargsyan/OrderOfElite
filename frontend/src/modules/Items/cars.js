import React, { useState, useEffect, useContext } from 'react'
import { request, formatMoney } from 'modules/Base'
import { UserPreviewCtx } from 'modules/Dashboard'

import apexTypeC200 from 'assets/pictures/cars/apex_type_c200.png'
import overlander from 'assets/pictures/cars/overlander.png'
import falkenGts from 'assets/pictures/cars/falken_gts.png'
import vanguard from 'assets/pictures/cars/vanguard.png'
import banshee from 'assets/pictures/cars/banshee.png'
import imperiumRArmored from 'assets/pictures/cars/imperium_r_armored.png'
import bordeauxV16 from 'assets/pictures/cars/bordeaux_v16.png'

const CAR_IMAGES = {
    apex_type_c200: apexTypeC200,
    overlander: overlander,
    falken_gts: falkenGts,
    vanguard: vanguard,
    banshee: banshee,
    imperium_r_armored: imperiumRArmored,
    bordeaux_v16: bordeauxV16,
}

function Cars() {
    const [cars, setCars] = useState(null)
    const { userPreviewData, updateUserPreviewData } = useContext(UserPreviewCtx)

    useEffect(() => {
        getCarsData()
    }, [])

    const getCarsData = () => {
        request({ url: 'items/get_user_cars', method: 'POST' })
            .then(response => setCars(response.data))
            .catch(error => console.error('Error getting cars data:', error))
    }

    const buyCar = (carKey) => {
        request({ url: 'items/buy_car', method: 'POST', data: { car_name: carKey } })
            .then(() => {
                alert('Car purchased successfully')
                updateUserPreviewData()
                getCarsData()
            })
            .catch(error => alert(error.response.data.message))
    }

    const sellCar = (carKey) => {
        request({ url: 'items/sell_car', method: 'POST', data: { car_name: carKey } })
            .then(() => {
                alert('Car sold successfully')
                updateUserPreviewData()
                getCarsData()
            })
            .catch(error => alert(error.response.data.message))
    }

    const equipCar = (carKey) => {
        request({ url: 'items/equip_car', method: 'POST', data: { car_name: carKey } })
            .then(() => {
                updateUserPreviewData()
                getCarsData()
            })
            .catch(error => alert(error.response.data.message))
    }

    const unequipCar = () => {
        request({ url: 'items/unequip_car', method: 'POST' })
            .then(() => {
                updateUserPreviewData()
                getCarsData()
            })
            .catch(error => alert(error.response.data.message))
    }

    if (cars === null) {
        return <div className="loading-text">LOADING...</div>
    }

    const garage = cars['__garage'] || { capacity: 0, used: 0 }
    const carEntries = Object.keys(cars).filter(k => k !== '__garage')
    const cityName = userPreviewData?.city || 'current city'

    return (
        <div>
            {/* Garage status bar */}
            <div className="garage-status-bar">
                <span className="garage-status-label">Garage</span>
                <span className="garage-status-count">
                    {garage.used} / {garage.capacity} slots used
                </span>
                {garage.capacity === 0 && (
                    <span className="garage-status-hint">Equip a house to unlock your garage</span>
                )}
            </div>

            {carEntries.map(carKey => {
                const car = cars[carKey]
                const owned = car.count_in_current_city > 0
                const equipped = car.is_equipped

                return (
                    <div className={`item-card ${equipped ? 'item-card--equipped' : ''}`} key={carKey}>
                        <img className="car-image" src={CAR_IMAGES[carKey]} alt={car.name} />
                        <div className="item-info">
                            <h2>
                                {car.name}
                                {equipped && <span className="item-equipped-badge">EQUIPPED</span>}
                            </h2>
                            <div className="item-owned-cities">
                                <span>Owned in {cityName}: </span>
                                <span style={{ color: owned ? '#66bb6a' : undefined, fontWeight: 'bold' }}>
                                    {car.count_in_current_city}
                                </span>
                            </div>
                            <p>Price: <strong className="item-price-value">{formatMoney(car.price)}</strong></p>
                            <p>Drive: {car.driving_multiplier}x</p>
                            <p>Defense: {car.defense_multiplier}x</p>
                            <p>Attack: {car.attack_multiplier}x</p>

                            <div className="item-action-row">
                                <button className="btn-buy" onClick={() => buyCar(carKey)}>Buy</button>
                                {owned && !equipped && (
                                    <button className="btn-equip" onClick={() => equipCar(carKey)}>
                                        Equip
                                    </button>
                                )}
                                {equipped && (
                                    <button className="btn-unequip" onClick={() => unequipCar()}>
                                        Unequip
                                    </button>
                                )}
                                {owned && (
                                    <button className="btn-sell" onClick={() => sellCar(carKey)}>Sell</button>
                                )}
                            </div>
                        </div>
                    </div>
                )
            })}
        </div>
    )
}

export default Cars