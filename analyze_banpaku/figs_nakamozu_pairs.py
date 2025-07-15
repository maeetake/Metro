import pandas as pd
import matplotlib.pyplot as plt
import os
import japanize_matplotlib

csv_file = 'sorted_output.csv'
output_dir = 'figs_nakamozu_pairs'
os.makedirs(output_dir, exist_ok=True)


df = pd.read_csv(csv_file, encoding='cp932')
df['data_date'] = pd.to_datetime(df['data_date'])


all_stations = set(df['depature_station'].unique()) | set(df['arrival_station'].unique())
all_stations.discard('なかもず') 

for station in all_stations:
    mask_nkz_to_other = (df['depature_station'] == 'なかもず') & (df['arrival_station'] == station)
    mask_other_to_nkz = (df['depature_station'] == station) & (df['arrival_station'] == 'なかもず')
    df_nkz_to_other = df[mask_nkz_to_other]
    df_other_to_nkz = df[mask_other_to_nkz]


    cnt_nkz_to_other = df_nkz_to_other.groupby('data_date').size()
    cnt_other_to_nkz = df_other_to_nkz.groupby('data_date').size()


    all_dates = pd.date_range(df['data_date'].min(), df['data_date'].max())
    cnt_nkz_to_other = cnt_nkz_to_other.reindex(all_dates, fill_value=0)
    cnt_other_to_nkz = cnt_other_to_nkz.reindex(all_dates, fill_value=0)


    plt.figure(figsize=(10, 5))
    plt.plot(all_dates, cnt_nkz_to_other, label=f'なかもず→{station}', marker='o')
    plt.plot(all_dates, cnt_other_to_nkz, label=f'{station}→なかもず', marker='o')
    plt.xlabel('日付')
    plt.ylabel('人数')
    plt.title(f'なかもず〜{station}間の利用者数（1日ごと・方向別）')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()


    filename = f'なかもず-{station}.png'
    plt.savefig(os.path.join(output_dir, filename))
    plt.close()

print(f"グラフ画像を「{output_dir}」フォルダに全駅分保存しました。")
