# Regras protegidas de empréstimos

Estas regras estão congeladas no arquivo `loan_rules.py` e cobertas por testes em `tests/test_loan_rules.py`.

Sempre rode este comando antes de mexer em empréstimos, pagamentos, dashboard ou fechamento de caixa:

```bash
python -m unittest tests.test_loan_rules
```

## Mensal
- Valor devido = principal + juros cadastrados.
- Vencimento por mês real, não por 30 dias.
- No dia do vencimento: status `Pagar hoje`.
- A partir do dia seguinte: multa diária por dia de atraso.
- Negociar juros: paga juros + multa e renova para o próximo mês mantendo o dia-base do empréstimo.
- Negociar quitação: encerra o contrato.

## Diário
- Valor devido = principal + juros cadastrados, parcelado por dia.
- Pode cobrar ou não aos domingos.
- Multa somente em blocos de 2 dias: 2, 4, 6, 8...
- Negociar juros: paga parcelas atrasadas + multa e vai para a próxima parcela do dia seguinte.
- Negociar quitação: encerra o contrato.

## Semanal
- Valor devido = principal + juros cadastrados, parcelado por semana.
- Vencimento sempre no mesmo dia da semana.
- Multa diária por cada parcela vencida e não paga.
- Negociar juros: paga parcelas atrasadas + multa e vai para a próxima parcela semanal pendente.
- Negociar quitação: encerra o contrato.
