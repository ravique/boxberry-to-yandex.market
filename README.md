# Library and script for Boxberry -> Yandex.Market API sync

# Disclaimer

This software created for specific purposes and definitely not a complete client. The workability was checked on Moscow and Moscow Region cities and points only. Can not work with other regions without rework, because region id for Yandex.Market is hardcoded and there is no method to get region codes from Yandex API.

**Works with**

[Boxberry New API](https://boxberry.ru/business_solutions/it_solutions/1089980/), [Yandex.Market Partner API](https://tech.yandex.com/market/partner/doc/dg/concepts/about-docpage/) 

# Functionality

- Gets detailed data about Boxberry points of selected regions and cities
- Pushes these points to the Yandex.Market (token is needed)
- Removes points from Yandex.Market if point does not exist in Boxberry response
- Writes all actions to the log (info level by default)

# Boxberry client API

- Get city ids of region
- Get points ids of city
- Get detailed data of a point

# Yandex.Market client API

- Get list of account existing points (outlets)
- Create new point (outlet)
- Delete point

# config.ini example

```ini
[Boxberry]
boxberry_token=<boxberry_token>
region_names=Московская
city_names=Москва


[YandexMarket]
ym_token=<yandex_market_token>
ym_client_id=<yandex_market_client_id>
campaign_id=<yandex_market_campaign_id>
delivery_cost=<fixed_delivery_cost_to_the_point>
min_delivery_days=<min_delivery_days>
max_delivery_days=<min_delivery_days>
```

# Launch params
```
-F, --force-update: Force updates all outlets with data from Boxberry. Default: False
```

# Roadmap

- <del>Yandex.Market API improvements (change point)</del>
- Use marshmallow to validate all point fields from Boxberry response
- Optional store points data in DB (Mongo? SQL?) to check updated data
- Unit tests  


## Authors

*Andrei Etmanov*

## License

This project is licensed under the MIT License – see the [LICENSE.md](LICENSE.md) file for details
