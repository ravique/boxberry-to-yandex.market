# Library and script for Boxberry -> Yandex.Market API sync

# Disclaimer

This software is still in development. 

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

# Delivery cost override

If you want to assign custom delivery cost for selected city OR region, add it to `delivery_cost_override` table. Fill only `city_name` or `region_name` field. Name must be equivalent to Boxberry `CityName` or `Area` field.  
**The name of the region in priority!**

# How it works

- Get list of available boxberry points in city/cities and region/regions, defined as 'region_names' and 'city_names' in config.ini. Note, that city and region names should be equivalent to Boxberry. 
- If launched with --update-regions param, updates or creates table in local db, that stores info about regions.
- Deletes all points, that yet exist in Yandex.Market, but not exist in Boxberry response.
- If launched with --force-update param, updates all points in Yandex.Market, that were found in Boxberry response
- Adds new found points to Yandex.Market
- Watch log for details

# config.ini example

```ini
[Boxberry]
boxberry_token=<boxberry_token>
region_names=<region name or region names, split by comma>
city_names=<city name or city names, split by comma>
target_start=<boxberry id of your drop off point> 
default_weight=<default parcel weight in grams>
picking_fee=<additional fee>
picking_time=<additional delivery time>
delivery_window=<difference between minimum and maximum delivery time>

[YandexMarket]
ym_token=<yandex_market_token>
ym_client_id=<yandex_market_client_id>
campaign_id=<yandex_market_campaign_id>

[General]
max_attempts=<sometimes, Yandex responds with 5xx code. number of attempts, default 10>
emails=<email/s of your shop, split by comma>
```

# Launch params
```
-F, --force-update: Force updates all outlets with data from Boxberry. Default: False

--UR, --update-regions: Creates (if does not exist) SQLite db and fills it with available city/region names and their id's from Yandex directory,
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
