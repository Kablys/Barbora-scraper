# -*- coding: utf-8 -*-
import scrapy
import re


class FoodSpider(scrapy.Spider):
    name = 'food'
    allowed_domains = ['barbora.lt']
    start_urls = [#'https://www.barbora.lt/darzoves-ir-vaisiai',
                   'https://www.barbora.lt/pieno-gaminiai-ir-kiausiniai',
                'https://www.barbora.lt/duonos-gaminiai-ir-konditerija',
                'https://www.barbora.lt/mesa-zuvys-ir-kulinarija,'
                'https://www.barbora.lt/bakaleja',
                'https://www.barbora.lt/saldytas-maistas',
                'https://www.barbora.lt/gerimai',
                #'https://www.barbora.lt/barbora-turgelis',
                  ]

    custom_settings = {
        'FEED_FORMAT': 'csv',
        'FEED_URI': 'food.csv',
        'FEED_EXPORT_ENCODING': 'utf-8',

        'AUTOTHROTTLE_ENABLED' : 'True',
        'AUTOTHROTTLE_START_DELAY' : '1.0',
        'AUTOTHROTTLE_MAX_DELAY' : '60.0',
        'AUTOTHROTTLE_TARGET_CONCURRENCY' : '1.0',

        'HTTPCACHE_ENABLED' : 'True',
        'HTTPCACHE_EXPIRATION_SECS' : '86400',  # 1 day.
    }

    def parse(self, response):
        # get item links
        for items in response.css('.b-product--imagelink::attr(href)').getall():
            next_page = response.urljoin(items)
            yield scrapy.Request(url=next_page, callback=self.parse_item)

        # go to next page
        next_page = response.css('.pagination li:last-child a::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_item(self, response):
        # Get float value from this data
        # €0,67
        # 579,00 kJ / 138,00 Kcal (second number)
        # 13,20 g
        def data_str_to_float (value):
            get_last_digits = '([\d,]+)($| \w+$)'
            #print(value)
            nutrition_string = re.search(get_last_digits, value).group(1)           
            return float(nutrition_string.replace(',','.'))

        # TODO some pages don't have data table, but have data with recommendet amounts
        nutrition_values = response.css('td::text').getall() # returns table as array (zipped)
        kcal=fat=s_fat=carbs=sugar=protein=salt=float('nan')
        for i, value in enumerate(nutrition_values):
            if   value == 'Energinė vertė' : kcal    = data_str_to_float(nutrition_values[i+1])
            elif value == 'Riebalai'       : fat     = data_str_to_float(nutrition_values[i+1])
            elif value == 'Sočiosios riebalų rūgštys': s_fat = data_str_to_float(nutrition_values[i+1])
            elif value == 'Angliavandeniai': carbs   = data_str_to_float(nutrition_values[i+1])
            elif value == 'Cukrūs'         : sugar   = data_str_to_float(nutrition_values[i+1])
            elif value == 'Baltymai'       : protein = data_str_to_float(nutrition_values[i+1])
            elif value == 'Druska'         : salt    = data_str_to_float(nutrition_values[i+1])
            elif value[0].isdigit():
                continue
            else:
                self.logger.warning('Unchecked nutrition value', value)

        crossed_out_price_str = response.css('.b-product-crossed-out-price::text').get()
        current_price_str = response.css('.b-product-price-current-number::text').get().strip() 
        original_price=discounted_price=float('nan')  
        if crossed_out_price_str:
            original_price = data_str_to_float(crossed_out_price_str)
            discounted_price = data_str_to_float(current_price_str)
        else :
            original_price = data_str_to_float(current_price_str)

        breadcrumbs = response.css('.breadcrumb span::text').getall()[1:-1]
        categorys = "\t".join(list(map(str.strip, breadcrumbs)))
        
        yield {
            'url' : response.request.url,
            'categorys' : categorys,
            'name' : response.css('.b-product-info--title::text').get(),
            'original price'   : original_price,
            'discounted price' : discounted_price,
            'amount' : int(response.css('.b-product-info--info1 dd:nth-child(4)::text').get()), # TODO make more precise
            #nutrition
            'kcal'   : kcal,
            'fat'    : fat,
            's_fat'  : s_fat,
            'carbs'  : carbs,
            'sugar'  : sugar,
            'protein': protein,
            'salt'   : salt,
            
        }
        pass

        