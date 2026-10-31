# flakehunt

[English](README.md) | [Русский](README.ru.md)

Скилл и CLI, которые заставляют работать с флаками честно: сначала докажи флак, потом почини и докажи починку.

Самая частая ложь в тестировании — «починил флак» без цикла прогонов, который раньше падал. Вторая по частоте — назвать флаком детерминированный фейл и перезапускать, пока «не пройдёт». `flakehunt` делает обе фразы невозможными случайно:

```text
$ flakehunt hammer "pytest -q tests/test_flaky.py" -n 20
command  pytest -q tests/test_flaky.py
runs     1:0 2:1 3:0 4:1 5:0 6:1
pattern  P F P F P F
verdict  FLAKY
advice   FLAKY confirmed: 3/6 passed, 3 failed. It's real. Bisect order/seed with the failing runs below...
```

## Что в репозитории

- **[skills/flaky-test-hunting](skills/flaky-test-hunting)** — процесс для агентов: подтверди флак (hammer), сузь причину (охота на сиды при зависимости от порядка, повторы при накоплении ресурсов, параллелизм для изоляции), почини самый узкий продемонстрированный механизм, затем прогони ровно тот пробник, что раньше падал. Оба `STABLE` — или не починено. Честный карантин: linked issue + срок годности, никогда тихий скип.
- **tools/flakehunt** — CLI ([README](tools/flakehunt/README.md)): `hammer` (цикл с ранней остановкой и строчкой паттерна P/F), `seeds` (какие именно значения сида воспроизводят падение), три вердикта с разными кодами выхода (`FLAKY`/`BROKEN`/`STABLE`), `--json` для CI, только stdlib.

## Установка

```bash
pip install flakehunt
npx skills add juzorei/flakehunt
```

## Ещё из портфеля

Один из серии прицельных наборов «скилл + CLI» одного автора:

- [ci-autopsy](https://github.com/juzorei/ci-autopsy) — классифицируй упавшие прогон до перезапуска
- [loglens](https://github.com/juzorei/loglens) — когда флак оставил след в логах
- [bumpmap](https://github.com/juzorei/bumpmap) — это апгрейд сломал или всё-таки флак?

Остальные — в [профиле juzorei](https://github.com/juzorei?tab=repositories).

## Рамки

Прогоняй пробники против своих сьютов; хаммеринг внешних сервисов перекладывает твою CI-нагрузку на чужие квоты — такие тесты должны сидеть за моками.

Лицензия MIT.
