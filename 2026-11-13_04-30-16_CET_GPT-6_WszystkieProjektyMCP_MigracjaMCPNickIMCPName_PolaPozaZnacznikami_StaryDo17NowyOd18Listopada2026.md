# Migracja deklaracji MCP_NICK i MCP_NAME: obowiązujący kontrakt

**Autor:** GPT-6. **Data:** 13.11.2026, Europe/Warsaw (CET).
**Cel:** poprawa błędnego umieszczenia nazw pól wewnątrz znaczników.
**Priorytet:** to jest nowsza, nadrzędna decyzja użytkownika. Zastępuje wszystkie wcześniejsze przykłady i instrukcje pokazujące stary format jako zalecany.

## 1. Nowy format: stosować natychmiast we WSZYSTKICH instrukcjach i generowanych wiadomościach

- `MCP_NICK:@@@NOVAECHOROMEO742@@@`
- `MCP_NAME:%%%Nazwa rozmowy%%%`

**Nazwa pola i dwukropek są POZA znacznikami**. Część `MCP_NICK` między `@@@` ma 7–20 liter i dokładnie 3 cyfry ASCII `0-9`. Nie sprawdzać słownika NATO, liczby słów, pisowni fragmentów ani ich znaczenia. `NOVA` jest poprawne. Trzy sklejone słowa to ewentualna sugestia konstruowania pseudonimu, nie warunek jego walidacji.

## 2. Okno przejściowe i automatyczny termin

| Czas w Europe/Warsaw | Nowy format | Stary format |
| --- | --- | --- |
| Do 17 listopada 2026, 23:59:59.999 CET włącznie | Akceptować | Akceptować tylko w wejściu, dla zgodności |
| Od 18 listopada 2026, 00:00:00 CET | Akceptować | Odrzucać jako wycofany |

Moment graniczny w UTC: **2026-11-17T23:00:00.000Z**.

Stary, wycofywany zapis:
- `@@@MCP_NICK:NOVAECHOROMEO742@@@`
- `%%%MCP_NAME:Nazwa rozmowy%%%`

Od teraz **nie wolno tworzyć ani pokazywać starych deklaracji** w promptach, README, AGENTS, CLAUDE, opisach narzędzi MCP, tekstach API ani nowych dokumentach, poza oznaczonymi przykładami zgodności wstecznej i historycznymi logami. Walidator obsługuje stare wejście do końca 17 listopada. Od 18 listopada wyłącza je automatycznie, bez ręcznej interwencji, restartu czy zmiany systemowego czasu.

## 3. Reguły walidacji i przechowywania

- Nowy nick JavaScript: `/^MCP_NICK:@@@([\p{L}]{7,20})([0-9]{3})@@@$/u`. W starym wariancie zmienia się wyłącznie rozmieszczenie nazwy pola i znaczników, nie reguła 7–20 liter i 3 cyfr.
- Nowe `MCP_NAME:` poprzedza `%%%`, a `%%%` obejmują tylko samą nazwę.
- Po wczytaniu deklaracji **normalizować oba wejściowe warianty do nowej postaci**. W bazie zachowywać niezmienną wewnętrzną wartość nicku i powiązania z prawdziwym MCP_ID, a nowe deklaracje zapisywać w nowej postaci.
- Historyczne zapisy w centralnej bazie muszą pozostać czytelne także po 18 listopada. **Zakaz akceptacji starego wejścia nie oznacza usunięcia istniejących relacji**.
- Przed nadaniem nowego nicku odczytać centralny rekord po rzeczywistym MCP_ID. Znany nick wykorzystać bez powtórnego pytania.
- Kolizje tożsamości rozstrzyga centralny rejestr, nie lokalny wymóg dodatkowej „własności nicku”.
- Przy błędnej deklaracji podać konkretną przyczynę: nazwa pola po niewłaściwej stronie, brak znacznika, 6/21 liter, 2/4 cyfry, niedozwolony znak, kolejność lub `STARY_FORMAT_*_WYLACZONY` po dacie. Nigdy nie uzasadniać odmowy brakiem słowa NATO.
- Błąd rejestracji nie może blokować niezależnych narzędzi MCP.

## 4. Odbiór i obowiązki w każdym projekcie

1. Znaleźć i zmienić wszystkie **aktywne instrukcje** i przykłady nowo generowanych deklaracji `MCP_NICK` i `MCP_NAME` na nowy format.
2. Parser przyjmuje nowy i stary format do 17.11, a od 18.11 wyłącznie nowy. Data przełączenia musi być porównywana według rzeczywistego czasu, nie zależeć od ręcznej aktualizacji.
3. Testować dzień 17.11 o 23:59:59.999 CET i 18.11 o 00:00:00.000 CET (równoważnie UTC 2026-11-17T23:00:00Z).
4. Sprawdzić odczyt historycznej tożsamości z Neo4j, łącznie z możliwością istnienia obu postaci danych bez fałszywego konfliktu.
5. Potwierdzić, że `MCP_NICK:@@@NOVAECHOROMEO742@@@` jest akceptowany. Walidacja słownikowa nadal jest **zabroniona**.
6. Udokumentować i wdrożyć zmianę do produkcji danego MCP. Sam dokument w GitHubie **nie oznacza**, że lokalny parser i serwer danego projektu zostały zmienione.

**LC MultiHost:** wzorcowa implementacja w gałęzi `feat/file-transfer-20261101`, commit `2974a6a01e7f3673a171734eb24d087b87c48450`. W innych repozytoriach właściciele kodu muszą odnieść tę zasadę do swoich faktycznych parserów, promptów, tool descriptions i usług.
