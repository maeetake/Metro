import os
import pandas as pd


script_dir = os.path.dirname(os.path.abspath(__file__))


input_filename = '202504-Nakamozu-OD.csv'
output_filename = 'sorted_output.csv'


input_csv = os.path.join(script_dir, input_filename)
output_csv = os.path.join(script_dir, output_filename)


df = pd.read_csv(input_csv, encoding="cp932")

df['data_date'] = pd.to_datetime(df['data_date'])
df['depature_station_time'] = pd.to_timedelta(df['depature_station_time'])

df_sorted = df.sort_values(['data_date', 'depature_station_time'])

df_sorted['data_date'] = df_sorted['data_date'].dt.strftime('%Y/%m/%d')
df_sorted['depature_station_time'] = df_sorted['depature_station_time'].apply(
    lambda x: '{:02}:{:02}:{:02}'.format(x.components.hours, x.components.minutes, x.components.seconds)
)

df_sorted.to_csv(output_csv, index=False, encoding="cp932")
