import argparse
import time
from datetime import date
from math import ceil

from db import session
from errors import PointParseError, ClientError, ClientConnectionError, ConfigError
from logger import logger
from client import BoxberryClient, BoxberryError, YandexMarketClient, convert_region_names_for_yandex
from config_parser import bxb_config, ym_config, general_config
from models import YandexRegion, DeliveryCostOverride
from phoneparser import parse_phone


def get_all_cities(region_names: list, city_names: list) -> list:
    region_city_codes = []
    if region_names:
        try:
            region_cities = bxb_client.get_cities_of_region(region_names=region_names)
        except BoxberryError as e:
            logger.error(msg='Can not get cities of regions: {}. {}'.format(str(region_names), e))
        else:
            try:
                region_city_codes = bxb_client.get_cities_codes(region_cities)
            except BoxberryError as e:
                logger.error(msg='Can not get city codes of region(s) {}. {}'.format(str(region_names), e))

    city_codes = []
    if city_names:
        try:
            city_codes = bxb_client.get_city_codes(city_names=city_names)
        except BoxberryError as e:
            logger.error(msg='Can not get city codes of city(es): {}. {}'.format(str(city_names), e))

    return region_city_codes + city_codes


def get_city_bxb_points(cities_list: list) -> set:
    points = []
    for code in cities_list:
        try:
            point = bxb_client.get_points_codes_list(code)
        except BoxberryError as e:
            logger.warning(msg='Points for city code {} did not found. {}'.format(code, e))
        else:
            points += point

    points_codes = [point['Code'] for point in points if point.get('Code', None)]
    return set(points_codes)


def update_rate(rate: int):
    return ceil(rate) // 10 * 10 + int(bxb_config['picking_fee'])


def get_rate_override(city: str = None, region: str = None):
    if region:
        override_rate_by_region = session.query(DeliveryCostOverride).filter_by(region_name=region).one_or_none()
        if override_rate_by_region:
            return override_rate_by_region

    if city:
        override_rate_by_city = session.query(DeliveryCostOverride).filter_by(city_name=city).one_or_none()
        if override_rate_by_city:
            return override_rate_by_city

    return False


def get_bxb_detailed_points(points_codes: set, exclude: set, target_start: str, default_weight: int) -> dict:
    if exclude:
        digit_exclude_codes = [code.replace('bxb_', '') for code in exclude]
        cleaned_points = points_codes - set(digit_exclude_codes)
        logger.info(msg='{} points yet exist in Yandex.Market'.format(len(points_codes) - len(cleaned_points)))
    else:
        cleaned_points = points_codes

    points_detailed_dict = dict()

    logger.info(msg='Begin to get detailed info about {} points'.format(len(cleaned_points)))
    for point_code in cleaned_points:
        try:
            detailed_point = bxb_client.get_point_info(point_code=point_code)
            time.sleep(1)

            override_rate = get_rate_override(city=detailed_point.get('CityName'), region=detailed_point.get('Area'))

            point_delivery_info = bxb_client.get_point_rate(
                point_code=point_code,
                default_weight=default_weight,
                target_start=target_start
            )

            for field in ('price', 'delivery_period'):
                if point_delivery_info.get(field, False) == False:
                    raise PointParseError(
                        'bxb did not return field {} for point {}. Point skipped'.format(field, point_code)
                    )

            if not override_rate:
                point_final_rate = update_rate(point_delivery_info.get('price'))
            else:
                point_final_rate = override_rate.rate
            min_delivery_days = int(point_delivery_info.get('delivery_period')) + int(bxb_config.get('picking_time', 0))
            max_delivery_days = min_delivery_days + int(bxb_config.get('delivery_window', 0))
            time.sleep(1)

            detailed_point.update({
                'rate': point_final_rate,
                'min_delivery_days': min_delivery_days,
                'max_delivery_days': max_delivery_days
            })

        except BoxberryError as e:
            logger.warning(msg='Detailed info about point {} did not found. {}'.format(point_code, e))
        except PointParseError as e:
            logger.warning(msg=e)
        else:
            points_detailed_dict['bxb_{}'.format(point_code)] = detailed_point

    logger.info(msg='Got {} points from Boxberry'.format(len(points_detailed_dict)))
    return points_detailed_dict


def get_yandex_region_id_from_db(ready_for_yandex_point) -> int:
    city_name = ready_for_yandex_point.get('CityName')
    region_name = ready_for_yandex_point.get('Area')

    region = session.query(YandexRegion).filter_by(
        city_name=city_name,
        region=region_name
    ).one_or_none()

    if not region:
        raise PointParseError('Code for {}, {} did not found in local db'.format(city_name, region_name))

    return region.yandex_id


def convert_bxb_to_ym(bxb_code: str, bxb_point: dict, emails: list) -> dict:
    name = bxb_point.get('Name')
    address = bxb_point.get('Address')
    phone = bxb_point.get('Phone')
    cost = bxb_point.get('rate')
    min_delivery_days = bxb_point.get('min_delivery_days')
    max_delivery_days = bxb_point.get('max_delivery_days')

    ready_for_yandex_point = convert_region_names_for_yandex(bxb_point)
    region_id = get_yandex_region_id_from_db(ready_for_yandex_point)

    fixed_phone = ''
    if phone:
        fixed_phone = parse_phone(phone)

    schedule_fields = (
        ('WorkMoBegin', 'WorkMoEnd', 'MONDAY',),
        ('WorkTuBegin', 'WorkTuEnd', 'TUESDAY',),
        ('WorkWeBegin', 'WorkWeEnd', 'WEDNESDAY',),
        ('WorkThBegin', 'WorkThEnd', 'THURSDAY',),
        ('WorkFrBegin', 'WorkFrEnd', 'FRIDAY',),
        ('WorkSaBegin', 'WorkSaEnd', 'SATURDAY',),
        ('WorkSuBegin', 'WorkSuEnd', 'SUNDAY'),
    )
    schedule = []

    for begin, end, ym_key in schedule_fields:
        if bxb_point.get(begin, False) and bxb_point.get(end, False):
            schedule.append(
                {
                    'startDay': ym_key,
                    'endDay': ym_key,
                    'startTime': bxb_point.get(begin),
                    'endTime': bxb_point.get(end)
                }
            )

    return {
        'name': name,
        'type': 'DEPOT',
        'isMain': False,
        'shopOutletCode': bxb_code,
        'visibility': 'VISIBLE',
        'address':
            {
                'regionId': region_id,
                'street': address
            },
        'phones':
            [fixed_phone],
        'workingSchedule':
            {
                'workInHoliday': False,
                'scheduleItems': schedule

            },
        'deliveryRules':
            [
                {
                    'cost': cost,
                    'minDeliveryDays': min_delivery_days,
                    'maxDeliveryDays': max_delivery_days,
                    'deliveryServiceId': 106
                }
            ],
        'emails':
            emails
    }


def delete_all_boxberry_points():
    existing_ym_codes = ym_client.get_outlets_by_type(outlet_type='bxb')
    for existing_code, existing_outlet in existing_ym_codes.items():
        ym_client.delete_outlet(existing_outlet.get('id'))


def update_regions_db():
    all_points = bxb_client.get_points_list()

    for point in all_points:
        point = convert_region_names_for_yandex(point)
        city_name = point.get('CityName')
        region = point.get('Area')

        city_instance = session.query(YandexRegion).filter_by(city_name=city_name, region=region).one_or_none()

        if not city_instance or city_instance.updated != date.today():
            try:
                region_id = ym_client.get_region_id(point)
            except ClientError:
                continue
            else:
                YandexRegion.create_or_update(city_name=city_name,
                                              yandex_id=region_id,
                                              region=region)


def delete_missing_outlets(existing_ym_codes, points_from_bxb_response):
    # Remove points from YandexMarket if not found on Boxberry
    prefixed_points_codes = ['bxb_{}'.format(point_code) for point_code in points_from_bxb_response]
    removed_points_count = 0

    for code, outlet in existing_ym_codes.items():
        if code not in prefixed_points_codes:
            try:
                ym_client.delete_outlet(outlet.get('id'))
            except ClientError or ClientConnectionError as e:
                logger.error(msg='Can not delete Boxberry point from Yandex.Market: {}'.format(e))
            else:
                removed_points_count += 1
                logger.info(
                    msg='Point id: {}, name: {} was deleted from Yandex.Market'.format(code, outlet.get('name')))

    logger.info(msg='Removed {} outlets from Yandex.Market'.format(removed_points_count))


def update_existing_outlets(existing_ym_codes, active_boxberry_points, emails):
    updated_outlets_count = 0

    for bxb_point_code, bxb_point in active_boxberry_points.items():
        if bxb_point_code in existing_ym_codes.keys():

            try:
                updated_point_data = convert_bxb_to_ym(bxb_point_code, bxb_point, emails)
            except PointParseError as e:
                logger.error(msg='Can not convert point data: {}'.format(e))
                continue
            try:
                ym_client.update_outlet(existing_ym_codes[bxb_point_code].get('id'), updated_point_data)
                time.sleep(1)
            except ClientError or ClientConnectionError as e:
                logger.error(msg='Can not update Boxberry point on Yandex.Market: {}'.format(e))
            else:
                updated_outlets_count += 1
                logger.info(msg='Point id: {}, address: {} was updated on Yandex.Market'.format(bxb_point_code,
                                                                                                bxb_point.get(
                                                                                                    'Address')))

    logger.info(msg='Updated {} outlets on Yandex.Market'.format(updated_outlets_count))


def add_new_outlets(existing_ym_codes, active_boxberry_points, emails):
    added_outlets_count = 0

    for bxb_point_code, bxb_point in active_boxberry_points.items():
        if bxb_point_code not in existing_ym_codes.keys():
            try:
                new_point = convert_bxb_to_ym(bxb_point_code, bxb_point, emails)
            except PointParseError as e:
                logger.error(msg='Can not convert point data: {}'.format(e))
                continue

            try:
                ym_client.post_outlet(new_point)
                time.sleep(1)
            except ClientError or ClientConnectionError as e:
                logger.error(msg='Can not add Boxberry point to Yandex.Market: {}'.format(e))
            else:
                added_outlets_count += 1
                logger.info(msg='New point id: {}, address: {} was added to Yandex.Market'.format(bxb_point_code,
                                                                                                  bxb_point.get(
                                                                                                      'Address')))
    logger.info(msg='Added {} outlets to Yandex.Market'.format(added_outlets_count))


# Setup clients

bxb_client = BoxberryClient(token=bxb_config['boxberry_token'])
ym_client = YandexMarketClient(
    ym_token=ym_config['ym_token'],
    ym_client_id=ym_config['ym_client_id'],
    ym_campaign_id=ym_config['campaign_id']
)


def run(update_existing: bool, run_update_db: bool):
    region_names = bxb_config.get('region_names')
    if region_names:
        region_names = region_names.split(',')

    city_names = bxb_config.get('city_names')
    if city_names:
        city_names = city_names.split(',')

    if not any((city_names, region_names)):
        raise ConfigError('region_names or city_names definition required in config')

    try:
        emails = general_config['emails'].split(',')
        target_start = bxb_config['target_start']
        default_weight = bxb_config['default_weight']
    except KeyError as e:
        raise ConfigError('{} definition required in config'.format(str(e)))

    if run_update_db:
        update_regions_db()

    existing_ym_codes = ym_client.get_outlets_by_type(outlet_type='bxb')
    logger.info(msg='Got {} existing Boxberry points from Yandex.Market'.format(len(existing_ym_codes)))

    if update_existing:
        exclude = set()
    else:
        exclude = set(existing_ym_codes.keys())

    if region_names == ['all']:
        points_from_bxb_response = bxb_client.get_points_codes_list()
    else:
        points_from_bxb_response = get_city_bxb_points(get_all_cities(region_names, city_names))

    active_boxberry_points = get_bxb_detailed_points(
        points_codes=points_from_bxb_response,
        exclude=exclude,
        target_start=target_start,
        default_weight=default_weight
    )

    delete_missing_outlets(existing_ym_codes, points_from_bxb_response)

    if update_existing:
        # Update existing points (outlets) on Yandex
        update_existing_outlets(existing_ym_codes, active_boxberry_points, emails)

    # Add new found points (outlets) to Yandex
    add_new_outlets(existing_ym_codes, active_boxberry_points, emails)


if __name__ == '__main__':
    bb_arg_parser = argparse.ArgumentParser(
        description='Analyses usage of words in functions, classes or variables names'
    )

    bb_arg_parser.add_argument(
        '-F',
        "--force-update",
        action='store_true',
        help='Force updates all outlets with data from Boxberry. Default: False'
    )

    bb_arg_parser.add_argument(
        '-UR',
        "--update-regions",
        action='store_true',
        help='Updates local db of Yandex region ids. Default: False'
    )

    args = bb_arg_parser.parse_args()

    run(args.force_update, args.update_regions)
