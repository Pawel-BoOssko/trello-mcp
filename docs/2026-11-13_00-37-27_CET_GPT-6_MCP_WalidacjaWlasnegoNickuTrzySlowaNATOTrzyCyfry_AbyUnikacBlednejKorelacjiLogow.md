# Obowiązująca zasada MCP_NICK: własny pseudonim, walidacja, logi

Data: 2026-11-13 00:37 CET. Autor: GPT-6.
Cel: jedna bezpieczna semantyka identyfikacji rozmów w projektach MCP, bez fałszywego łączenia historii innych czatów.
Status w tym repozytorium: wymaganie do uwzględnienia przy najbliższej modyfikacji MCP; niniejszy dokument nie oznacza, że kod już je implementuje.

## Format
- MCP_NICK należy do jednej konkretnej rozmowy i nie zmienia się przy zmianie nazwy.
- Ma dokładnie trzy **pełne** słowa alfabetu NATO, bez separatorów, a na końcu dokładnie trzy cyfry od 0 do 9.
- Zestaw wyrazów: ALFA, BRAVO, CHARLIE, DELTA, ECHO, FOXTROT, GOLF, HOTEL, INDIA, JULIETT, KILO, LIMA, MIKE, NOVEMBER, OSCAR, PAPA, QUEBEC, ROMEO, SIERRA, TANGO, UNIFORM, VICTOR, WHISKEY, XRAY, YANKEE, ZULU.
- Minimalnie 12 liter i 3 cyfry, łącznie 15 znaków pseudonimu. Maksymalnie 24 litery i 3 cyfry, łącznie 27 znaków. Same litery i cyfry nie wystarczą: część literowa musi składać się z trzech całych wyrazów NATO.
- Zapis kanoniczny wielkimi literami; wyrazy mogą się powtarzać. Przykładowa sama wartość bez znacznika: KILOLIMASIERRA583.
- Znacznik deklaracji składa się kolejno z trzech znaków @, napisu MCP_NICK:, własnej wartości i trzech znaków @ na końcu.
- Nie umieszczamy w dokumentacji pełnego, poprawnego znacznika z cudzym przykładowym pseudonimem, ponieważ parsery logów mogą potraktować go jak rzeczywistą identyfikację.

## Reguła własności i komunikacji
- Czat może wypisywać kompletny znacznik trzech małp **wyłącznie dla własnego MCP_NICK**.
- Przy wybudzeniu lub przypomnieniu znacznik odbiorcy umieszczamy w przesyłanej wiadomości, aby był widoczny w historii.
- Identyfikatory innych czatów, w tym zlecającego, wykonawcy, poprzednika i następcy, pokazujemy bez ich znaczników trzech małp.
- Przy przekazaniu nowego zadania zlecającemu wystarczy jego logiczny identyfikator zadania, np. KILOLIMASIERRA583.01. Instancja może mieć nazwę KILOLIMASIERRA583.01.01, po rotacji KILOLIMASIERRA583.01.02.
- Przy każdym kontakcie MCP należy sparsować deklaracje pomiędzy potrójnymi małpami i odrzucić niedomknięty znacznik, błędną liczbę cyfr, cyfry w części słownej, niepełny wyraz NATO, niedozwolone znaki i konflikt z zapisanym pseudonimem.
- Sama zgodność składniowa nie dowodzi właściciela. Porównanie z tożsamością aktualnej sesji oraz centralnym rejestrem jest osobnym krokiem.

## Pozostałe identyfikatory
- MCP_NAME: zmienna nazwa opisowa; jej deklaracja ma trzy znaki % przed i po wartości z prefiksem MCP_NAME:.
- MCP_ID: identyfikator znany serwerowi MCP. UUID: identyfikator rozmowy ChatGPT. UI_NAME: nazwa w interfejsie. To różne pola.
- Brakujących wartości nie wymyślamy; identyczny UI_NAME nie pozwala scalać różnych UUID.
- Źródłem centralnym jest Neo4j na SATANAMD: D:\projects\chatgpt-identity-graph, a odczyt służy wyłącznie potrzebom konkretnego zadania. Rejestr ma własne istniejące importery, z opóźnieniem dochodzącym do około 10 minut; nie budować równoległego.

## Testy przy wdrożeniu
1. Poprawne trzy pełne słowa i trzy cyfry, długość minimum 15.
2. Odrzucenie cyfr przed końcem, błędnych końcówek, niedomkniętych małp i niepełnych wyrazów NATO.
3. Zgodność nicku we wszystkich kontaktach i brak automatycznego nadpisania na podstawie samego tytułu.
4. W wybudzeniu znacznik wyłącznie odbiorcy; w powiadomieniu zlecającego wyłącznie zlecającego.
5. Odczyt z Neo4j przy brakujących identyfikatorach, bez wielokrotnego odpytywania po ustaleniu danych.
6. Poprawne powiązanie logicznego zadania z kolejnymi instancjami rotacyjnymi.

Należy dopisać to do planu zadań każdego utrzymywanego serwera MCP i zapewnić testy przed produkcyjnym wdrożeniem kodu.
