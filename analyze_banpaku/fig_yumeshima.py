import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib


df = pd.read_csv('sorted_output.csv', encoding='cp932')
df['data_date'] = pd.to_datetime(df['data_date'])

mask_nkz_to_ym = (df['depature_station'] == 'なかもず') & (df['arrival_station'] == '夢洲')
mask_ym_to_nkz = (df['depature_station'] == '夢洲') & (df['arrival_station'] == 'なかもず')

df_nkz_to_ym = df[mask_nkz_to_ym]
df_ym_to_nkz = df[mask_ym_to_nkz]

cnt_nkz_to_ym = df_nkz_to_ym.groupby('data_date').size()
cnt_ym_to_nkz = df_ym_to_nkz.groupby('data_date').size()

plt.figure(figsize=(10, 5))
plt.plot(cnt_nkz_to_ym.index, cnt_nkz_to_ym.values, label='なかもず→夢洲', marker='o')
plt.plot(cnt_ym_to_nkz.index, cnt_ym_to_nkz.values, label='夢洲→なかもず', marker='o')
plt.xlabel('日付')
plt.ylabel('人数')
plt.title('なかもず〜夢洲間の利用者数（1日ごと・方向別）')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
