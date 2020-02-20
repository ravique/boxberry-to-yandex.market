import argparse
import time

from errors import PointParseError, ClientError, ClientConnectionError
from logger import logger
from client import BoxberryClient, BoxberryError, YandexMarketClient
from config_parser import bxb_config, ym_config
from phoneparser import parse_phone


def get_all_cities(bxb_client: BoxberryClient) -> list:
    region_names = bxb_config['region_names'].split(',')
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

    city_names = bxb_config['city_names'].split(',')
    city_codes = []
    if city_names:
        try:
            city_codes = bxb_client.get_city_codes(city_names=city_names)
        except BoxberryError as e:
            logger.error(msg='Can not get city codes of city(es): {}. {}'.format(str(city_names), e))

    return region_city_codes + city_codes


def get_city_bxb_points(bxb_client: BoxberryClient, cities_list: list) -> set:
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


def get_bxb_detailed_points(bxb_client: BoxberryClient, points_codes: set, exclude: set) -> dict:
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
        except BoxberryError as e:
            logger.warning(msg='Detailed info about point {} did not found. {}'.format(point_code, e))
        else:
            points_detailed_dict['bxb_{}'.format(point_code)] = detailed_point

    return points_detailed_dict


def convert_bxb_to_ym(bxb_code: str, bxb_point: dict) -> dict:
    name = bxb_point.get('Name')
    address = bxb_point.get('Address')
    phone = bxb_point.get('Phone')
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
                'regionId': 213,
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
                    'cost': ym_config['delivery_cost'],
                    'minDeliveryDays': ym_config['min_delivery_days'],
                    'maxDeliveryDays': ym_config['max_delivery_days'],
                    'deliveryServiceId': 106
                }
            ],
        'emails':
            ['info@medovayalavka.ru']
    }


def delete_all_boxberry_points():
    ym_client = YandexMarketClient(
        ym_token=ym_config['ym_token'],
        ym_client_id=ym_config['ym_client_id'],
        ym_campaign_id=ym_config['campaign_id']
    )
    existing_ym_codes = ym_client.get_outlets_by_type(outlet_type='bxb')
    for existing_code, existing_outlet in existing_ym_codes.items():
        ym_client.delete_outlet(existing_outlet.get('id'))


def run(update_existing: bool, ):
    bxb_client = BoxberryClient(token=bxb_config['boxberry_token'])
    ym_client = YandexMarketClient(
        ym_token=ym_config['ym_token'],
        ym_client_id=ym_config['ym_client_id'],
        ym_campaign_id=ym_config['campaign_id']
    )

    existing_ym_codes = ym_client.get_outlets_by_type(outlet_type='bxb')
    logger.info(msg='Got {} existing Boxberry points from YM'.format(len(existing_ym_codes)))

    if update_existing:
        exclude = set()
    else:
        exclude = set(existing_ym_codes.keys())

    all_points_in_cities = get_city_bxb_points(bxb_client, get_all_cities(bxb_client))

    active_boxberry_points = get_bxb_detailed_points(
        bxb_client,
        points_codes=all_points_in_cities,
        exclude=exclude
    )

    logger.info(msg='Got {} points from Boxberry'.format(len(active_boxberry_points)))

    # Remove points from YandexMarket if not found on Boxberry
    prefixed_points_codes = ['bxb_{}'.format(point_code) for point_code in all_points_in_cities]
    removed_points_count = 0

    for code, outlet in existing_ym_codes.items():
        if code not in prefixed_points_codes:
            try:
                ym_client.delete_outlet(outlet.get('id'))
            except ClientError or ClientConnectionError as e:
                logger.error(msg='Can not delete Boxberry point from YM: {}'.format(e))
            else:
                removed_points_count += 1
                logger.info(msg='Point id: {}, name: {} was deleted from YM'.format(code, outlet.get('name')))

    logger.info(msg='Removed {} outlets from YM'.format(removed_points_count))

    if update_existing:
        # Update existing points (outlets) on Yandex

        updated_outlets_count = 0
        for bxb_point_code, bxb_point in active_boxberry_points.items():
            if bxb_point_code in existing_ym_codes.keys():
                try:
                    updated_point_data = convert_bxb_to_ym(bxb_point_code, bxb_point)
                except PointParseError as e:
                    logger.error(msg='Can not convert point data: {}'.format(e))
                    continue
                try:
                    ym_client.update_outlet(existing_ym_codes[bxb_point_code].get('id'), updated_point_data)
                    time.sleep(1)
                except ClientError or ClientConnectionError as e:
                    logger.error(msg='Can not update Boxberry point on YM: {}'.format(e))
                else:
                    updated_outlets_count += 1
                    logger.info(msg='Point id: {}, address: {} was updated on YM'.format(bxb_point_code,
                                                                                         bxb_point.get('Address')))

        logger.info(msg='Updated {} outlets on YM'.format(updated_outlets_count))

    # Add new found points (outlets) to Yandex

    added_outlets_count = 0
    for bxb_point_code, bxb_point in active_boxberry_points.items():
        if bxb_point_code not in existing_ym_codes.keys():
            try:
                new_point = convert_bxb_to_ym(bxb_point_code, bxb_point)
            except PointParseError as e:
                logger.error(msg='Can not convert point data: {}'.format(e))
                continue
            try:
                ym_client.post_outlet(new_point)
                time.sleep(1)
            except ClientError or ClientConnectionError as e:
                logger.error(msg='Can not add Boxberry point to YM: {}'.format(e))
            else:
                added_outlets_count += 1
                logger.info(msg='New point id: {}, address: {} was added to YM'.format(bxb_point_code,
                                                                                       bxb_point.get('Address')))
    logger.info(msg='Added {} outlets to YM'.format(added_outlets_count))


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

    args = bb_arg_parser.parse_args()

    run(args.force_update)
