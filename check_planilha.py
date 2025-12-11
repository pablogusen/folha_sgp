import pandas as pd

df = pd.read_excel('Relatorio-Consigno-MargemConsignavel-07122025.xlsx', skiprows=2)
df.columns = ['Numero', 'Funcionario', 'Matricula', 'CPF', 'Col4', 'Col5', 'Col6', 'Col7', 
              'Col8', 'Col9', 'Col10', 'Col11', 'Col12', 'Col13', 'Col14', 'Col15', 
              'Col16', 'Data', 'Hora', 'Orgaos', 'Observacao']

print(f"Total de linhas: {len(df)}")
print(f"\nPrimeiras 5 linhas:")
for i in range(min(5, len(df))):
    print(f"Linha {i}: {df.iloc[i]['Funcionario']}")
