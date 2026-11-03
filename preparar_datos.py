"""Recupera la escala original (US$) del csv_limpio.csv de la Fase I invirtiendo RobustScaler:
x = x' * IQR + mediana. Medianas e IQR provienen de df_eda.describe() del notebook (celda 12).
imei tiene IQR = 0 (sklearn usa escala 1). Salida: ehpm2021_escala_original.csv (base del dashboard)."""
import pandas as pd
d = pd.read_csv('csv_limpio.csv', sep=';')
P = {'r021a':(4,2),'imeds':(0,91),'imei':(0,1),'ingfa':(503,543.91),'ingpe':(134.17,138.05),'ingre':(0,260),
     'gmed':(0,18),'gmem':(0,60.67),'gmvi':(55,63.66),'totayuda':(0,25)}
o = d.copy()
for c,(m,s) in P.items(): o[c] = d[c]*s + m
o['r021a'] = o['r021a'].round().astype(int)
o['ingreso_por_miembro'] = o.ingfa/o.r021a
o.drop(columns=[]).round(2).to_csv('ehpm2021_escala_original.csv', index=False)
