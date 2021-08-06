import requests
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
from waveshare_epd import epd7in5_V2
import time
import logging

logging.basicConfig(level=logging.ERROR)


class NsItem:
    def __init__(self, data, measure='mmol'):
        id = data['_id']
        device = data['device']
        self.timestamp = data['date']
        self.sgv = data['sgv']
        self.delta_data = data['delta']
        self.direction = data['direction']

        self.setting = measure

    @property
    def bg(self):
        if self.setting == 'mmol':
            return round(self.mg_to_mmol(self.sgv), 1)
        else:
            return self.sgv

    @property
    def delta(self):
        if self.setting == 'mmol':
            return round(self.mg_to_mmol(self.delta_data), 1)
        else:
            return self.delta_data

    @property
    def time(self):
        trunked_timestamp = float(str(self.timestamp)[0: 10])
        return datetime.fromtimestamp(trunked_timestamp).strftime("%H:%M")

    @property
    def elapsed_time(self):
        trunked_timestamp = float(str(self.timestamp)[0: 10])
        ns_time = datetime.fromtimestamp(trunked_timestamp)
        now = datetime.now()
        time_difference = now - ns_time
        minutes = time_difference.total_seconds() / 60
        return round(minutes)

    @staticmethod
    def mg_to_mmol(value):
        return (value / 18.01)

    @classmethod
    def ns_query(cls, address, count=100):
        address = address
        number_of_query = count
        complete_address = address + '/api/v1/entries/sgv.json'
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        response = requests.get(complete_address, headers=headers, params={'count': number_of_query})
        if response.status_code == 200:
            json_data = response.json()

        data_list = []
        for item in reversed(json_data):
            data_list.append(cls(item))

        return data_list


class EpdContextManager:
    def __init__(self):
        self.epd = epd7in5_V2.EPD()

    def __enter__(self):
        return self.epd

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.epd.init()
        self.epd.Clear()
        epd7in5_V2.epdconfig.module_exit()


def graph(data):
    xpoints = np.array([item.time for item in data])
    ypoints = np.array([item.bg for item in data])

    px = 1 / plt.rcParams['figure.dpi']
    plt.figure(figsize=(800*px, 480*px))
    plt.plot(xpoints,
             ypoints,
             # marker='.',
             linestyle='--',
             color='black')
    plt.gcf().autofmt_xdate()
    plt.xticks(xpoints[::5], rotation=45, ha='right')
    plt.ylim([2, 15])

    plt.grid()
    canvas = plt.get_current_fig_manager().canvas
    canvas.draw()
    pil_image = Image.frombytes('RGB', canvas.get_width_height(), canvas.tostring_rgb())
    return pil_image


def compositing(pillow, ns_value):
    img = pillow
    draw = ImageDraw.Draw(img)
    font_path = ('OpenSans-Regular.ttf')
    font1 = ImageFont.truetype(font_path, 60)
    font2 = ImageFont.truetype(font_path, 17)
    draw.text((150, 70), str(ns_value.bg), font=font1, fill=(0, 0, 0))
    draw.text((150, 140), 'Delta: ' + str(ns_value.delta), font=font2, fill=(0, 0, 0))
    data_time = 'Last reading: {}'.format(str(ns_value.time))
    draw.text((150, 160), data_time, font=font2, fill=(0, 0, 0))

#    img.show()
    return img


def main():
    query = NsItem.ns_query('https://diagoup.herokuapp.com', 100)

    with EpdContextManager() as epd:
        first_loop = True
        while True:
            if first_loop is not True:
                single_item_query = NsItem.ns_query('https://diagoup.herokuapp.com', 1)
                query.pop(0)
                query.append(single_item_query[0])
            first_loop = False

            epd.init()
            ploted = graph(query)
            composited = compositing(ploted, query[-1])
            epd.display(epd.getbuffer(composited))
            epd.sleep()
            while query[-1].elapsed_time < 5:
                time.sleep(60 * 2)


def test():
    query = NsItem.ns_query('https://diagoup.herokuapp.com', 100)
    ploted = graph(query)
    composited = compositing(ploted, query[-1])


if __name__ == '__main__':
    main()
    #test()
