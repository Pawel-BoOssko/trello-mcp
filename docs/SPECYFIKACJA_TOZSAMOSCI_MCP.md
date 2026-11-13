# Specyfikacja centralnej identyfikacji i synchronizacji czatów MCP
Data: 2026-11-13. Status: uzgodnione zasady do wdrożenia.

## Cel i pięć pól
UUID, MCP_ID, MCP_NICK, folder roboczy, nazwa czatu. UUID, MCP_ID i MCP_NICK są trwałe, unikalne i związane 1:1. MCP_ID pochodzi z metadanych koperty żądania MCP i jest niewidoczny dla modelu do chwili ujawnienia przez serwer. Folder przypisany do czatu jest trwały, ale jeden folder może obsługiwać wiele czatów. Nazwa rozmowy jest pomocnicza i zmienna; nie przechowujemy historii nazw.

## MCP_NICK
Jedyna obowiązkowa deklaracja modelu, jeśli nie jest już znana centralnemu rejestrowi. Model powinien wymyślić trzy słowa NATO i trzy cyfry bez spacji, ale nie weryfikujemy słownika NATO. Akceptowane oba formaty:
MCP_NICK:@@@ALFABRAVOCHARLIE742@@@
@@@MCP_NICK:ALFABRAVOCHARLIE742@@@
Walidacja syntaktyczna: wyłącznie litery i dokładnie trzy cyfry na końcu, właściwe znaczniki @@@; np. NOVAECHOROMEO742 jest poprawne. Regexy:
^MCP_NICK:@@@[A-Za-z]+[0-9]{3}@@@$
^@@@MCP_NICK:[A-Za-z]+[0-9]{3}@@@$

## Neo4j — źródło prawdy
Centralny rejestr jest nadrzędny. Dopisujemy tylko brakujące informacje; nie nadpisujemy istniejących powiązań. Sprzeczność UUID ↔ MCP_ID jest krytycznym alarmem integralności: blokada sprzecznego zapisu, precyzyjna diagnostyka, bez cichej naprawy. Gdy model poda nowy MCP_NICK albo inny folder niż już zarejestrowany, serwer zwraca obowiązującą wartość i nakazuje jej używanie. Powiązania mają być unikalne, atomowe, idempotentne i odporne na równoczesne zgłoszenia.

## Pierwsze wywołanie i synchronizacja
Przy pierwszym kontakcie serwer zbiera MCP_ID z metadanych, UUID z wiarygodnego źródła/rejestru, MCP_NICK od modelu, folder i ewentualną aktualną nazwę. Odczytuje Neo4j, weryfikuje spójność, dopisuje tylko brakujące wartości i zwraca klientowi wszystkie znane spośród pięciu pól. Pełna synchronizacja jednorazowa; kolejne wywołania korzystają z utrwalonego powiązania. Brakujące informacje mogą być później uzupełniane bez nadpisywania.

## Propagacja
Po synchronizacji serwer prosi model o jednorazowe wyświetlenie wszystkich znanych identyfikatorów w interfejsie oraz upewnienie się, że zapisano je w odpowiednim miejscu folderu roboczego. Celem jest późniejsze wyszukiwanie i łączenie danych w logach, plikach, rozmowach i innych kanałach.

## Folder roboczy
Serwer pyta: Podaj swój folder roboczy; jeśli nie masz, nie twórz go samodzielnie — przydzielimy Ci go. Jeśli Neo4j ma przypisanie, jest ono ostateczne. Jeśli nie ma, można przypisać wskazany istniejący folder. Jeśli klient nie ma folderu, serwer sprawdza istniejący przydział, a następnie tworzy w ustalonej lokalizacji folder o nazwie MCP_ID, zapisuje ścieżkę w Neo4j i zwraca ją modelowi. Lokalizacja bazowa wymaga ustalenia. Folder może być współdzielony, a nazwa wskazywać czat, dla którego pierwotnie powstał.

## Diagnostyka błędów
Każdy błąd klienta musi zawierać: pole, otrzymaną wartość (jeśli bezpieczna), oczekiwaną wartość lub format, konkretną przyczynę, dokładną instrukcję poprawy, przykład i informację o ponowieniu. Błędne wywołanie traktujemy przede wszystkim jako dowód niewystarczających instrukcji przekazanych klientowi. Nie wystarczą ogólne invalid identity, bad request, registration_pending.

## Reguła nadrzędna
Identyfikujemy raz, synchronizujemy dwukierunkowo, zapisujemy trwale, nie nadpisujemy ustalonych powiązań i propagujemy wszystkie znane informacje. Nie tworzymy historii nazw rozmów.
## Aneks techniczny Neo4j — kontrakt współpracy dla wszystkich serwerów MCP
Data aneksu: 2026-11-13. Odpowiedzialny: projekt ChatGPT Identity Graph na SATANAMD.

### 1. Rozdzielenie odpowiedzialności i dostępne interfejsy

**Neo4j na SATANAMD** jest trwałym rejestrem powiązań. Serwery MCP (LC MultiHost, OpenFill, FaultHarbor, pozostałe) są klientami synchronizacji, a nie niezależnymi bazami nadrzędnymi. Powinny przekazywać do jednego rejestru tylko fakty pozyskane z wiarygodnego źródła, bez wymyślania brakujących pól.

Katalog kodu: \`D:\projects\chatgpt-identity-graph\`. Aktualne interfejsy:
- Lokalny API HTTP: \`http://127.0.0.1:18765\`, uruchamiany jako \`ChatGPT-Identity-Registry-API\` przez Harmonogram Windows. GET \`/health\` (diagnostyka bez hasła), GET \`/v1/identity/lookup?kind=UUID&value=...\`, GET \`/v1/status\`, POST \`/v1/identity/sync\`. Operacje inne niż \`/health\` wymagają tokenu Bearer przechowywanego wyłącznie na komputerze.
- Osobny **MCP read-only** \`neo4j-identity\`: skrypt \`mcp_identity_server.py\`, narzędzia \`identity_lookup\`, \`identity_search_chats\`, \`identity_describe_chat\`, \`identity_get_workdirs\`, \`identity_health\`. Nie udostępnia ogólnego Cypher ani funkcji usuwania danych. W Claude Code na SATANAMD został przetestowany protokół MCP i zarejestrowany **user-scope**, co czyni go dostępnym we wszystkich projektach tego klienta.
- HTTP MCP: dodatkowy transport port \`127.0.0.1:18766/mcp\`, uruchamiany przez \`ChatGPT-Identity-Neo4j-MCP-HTTP\`, z obowiązkowym nagłówkiem Authorization: Bearer. Sam port lokalny nie jest publicznym adresem ani automatyczną instalacją w ChatGPT/Claude Cloud. Żadnego klucza nie wklejać do dokumentacji lub Git.
- CLI awaryjny na SATANAMD: \`python D:\projects\chatgpt-identity-graph\graph.py find UUID <uuid>\`, \`graph.py search "fragment nazwy"\`, \`graph.py describe <uuid>\`, \`status.py\`. Parametr \`--requester\` identyfikuje wywołującego, gdy rzeczywiście jest znany. Nie wymyślać go.
- Standardowa ścieżka **zapisu**: uwierzytelniony transport LC MultiHost lub POST \`/v1/identity/sync\`. Nie zapisywać bezpośrednio zapytań Cypher z dowolnego serwera MCP. Weryfikacja po zapisie musi pochodzić z ponownego odczytu Neo4j.

### 2. Model danych i korespondencja pięciu pól

W praktycznej implementacji występują \`(:Identity {kind:'UUID'|'MCP_ID'|'MCP_NICK'|'UI_NAME', value:'...'})\` i relacje \`[:POWIAZANY]\`. Katalogi to \`(:WorkingFolder {key,path,host})\` i \`[:WORKS_IN]\`; ich pochodzenie jest zachowywane w \`WorkingFolderEvidence\`. Jeden folder może mieć wielu właścicieli. \`UI_NAME\` nie jest kluczem tożsamości: ten sam tytuł mogą mieć różne czaty. Dla porządku istnieją także \`ChatProject\` i relacje \`IN_PROJECT\`.

Semantyka:
- **UUID**: identyfikator rozmowy z wiarygodnego adresu/źródła, dokładnie 36 znaków. Nie zastępować go tytułem, folderem ani nazwą MCP.
- **MCP_ID**: identyfikator rzeczywistej sesji z koperty MCP. Nagłówek \`X-Openai-Session\` lub \`params._meta["openai/session"]\`. Serwer zna go niezależnie od modelu; model nie może sam go wymyślić.
- **MCP_NICK**: trwały pseudonim. Jego deklarację przy pierwszym kontakcie należy uzupełnić, jeżeli rejestr go jeszcze nie zna. Uzgodniona w niniejszej specyfikacji walidacja (litery + 3 cyfry, prawidłowe znaczniki) ma pierwszeństwo przed wcześniejszymi eksperymentami z obowiązkowymi słowami NATO.
- **Folder roboczy**: pełna ścieżka Windows (oraz host) przypisana do identyfikatora czatu. Może być współdzielona; z samej nazwy folderu nie wolno zgadywać UUID. Jeśli już istnieje autorytatywne przypisanie, nie podmieniać go ścieżką zasugerowaną przez model.
- **Nazwa rozmowy** (\`UI_NAME\`): obecny opis użytkowy. Nie używać jej do scalania silnych identyfikatorów. Nowa polityka z dokumentu głównego: nie budować historii zmian nazw na potrzeby bieżącej tożsamości.

**Stan przejściowy wymagający ostrożności:** dotychczasowy graf zawiera pomocnicze historyczne \`ChatNameEvidence\`, powstałe przed obecną decyzją o rezygnacji z historii nazw. To dane legacy; nie oznacza, że dokument główny zmieniono. Ich ewentualne usunięcie wymaga osobnej migracji z kontrolą, żeby nie zerwać poprawnych powiązań. Do bieżących operacji stosować aktualną nazwę i pięć uzgodnionych pól.

### 3. Procedura przy pierwszym kontakcie MCP

1. Odczytaj **MCP_ID** z metadanych żądania po stronie serwera, a nie z niezweryfikowanego tekstu modelu. Sprawdź lokalny cache sesji i centralny rejestr.
2. Jeżeli jest zapis MCP_ID, pobierz wszystkie znane pola; nie żądaj nowego MCP_NICK ani nowego folderu, jeśli już mają wartości. Zwróć dane do modelu i kontynuuj pierwotne narzędzie.
3. Jeżeli nowa sesja nie ma nicku, poproś model o deklarację \`MCP_NICK\` we właściwej składni. Brak nicku może być stanem przejściowym \`BRAK_MCP_NICK\`, ale nie może blokować niezależnych poleceń.
4. Jeśli znany jest rzeczywisty UUID albo folder roboczy, dołącz je wraz ze źródłem. **Nie wnioskuj UUID z samego tytułu**. Gdy folderu brak, najpierw sprawdź istniejące przypisanie w Neo4j; potem realizuj regułę przydziału z dokumentu głównego, po ustaleniu bazowej lokalizacji i bez duplikowania katalogów.
5. Przeprowadź atomową walidację silnych powiązań. Konflikt UUID↔MCP_ID lub MCP_NICK z innym czatem to blokada sprzecznego **zapisu**, precyzyjny komunikat i zgłoszenie do diagnostyki/FaultHarbor, a nie nadpisanie i nie scalenie po tytule.
6. Wpisz tylko brakujące pola, po czym ponownie odczytaj tożsamość. Zwróć modelowi wszystkie znane spośród pięciu pól i wyraźnie wskaż pola brakujące.
7. Jednorazowo poproś model o pokazanie znanych identyfikatorów i ich utrwalenie w odpowiednim dokumencie folderu roboczego. Kolejne wywołania nie powtarzają tego bez potrzeby.
8. Powtórne dostarczenie tych samych danych ma dać wynik idempotentny. Równoległe zgłoszenia wymagają transakcji i ograniczeń unikalności w Neo4j.

### 4. Reguły błędów, dostępności i bezpieczeństwa

Każdy błędny argument musi zwracać co najmniej: \`field\`, \`received\` (tylko gdy ujawnienie bezpieczne), \`expected\`, \`reason\`, \`fix\`, \`example\` i \`retryable\`. \`registry_unavailable\` jest błędem infrastruktury, nie powodem do dopisania losowego identyfikatora. Dla niedostępności Neo4j pozostałe niezależne narzędzia MCP powinny działać; operacje zapisu tożsamości należy odroczyć lub zachować w kontrolowanej kolejce, a nie udawać sukcesu.

Nie przesyłać tokenu dostępu do Neo4j, hasła Bolt ani adresu prywatnego do publicznych repozytoriów. Nie dawać klientom MCP ogólnego wykonania Cypher. Dostęp do czytania grafu z innych komputerów powinien odbywać się przez chroniony transport i wymagać autoryzacji. Tokeny są własnością instalacji, nie rozmowy. Wszystkie żądania i błędy mają własny dziennik audytu.

### 5. Operacyjne testy i odpowiedzialność

Na SATANAMD: \`claude mcp get neo4j-identity\`, \`claude mcp list\`, test \`identity_health\` i \`identity_describe_chat\` przez klienta MCP; \`python D:\projects\chatgpt-identity-graph\status.py\` dla awarii synchronizacji. Przy zmianie danych rejestru sprawdź wynik importu, różnicę liczników i zgodność UUID/MCP_ID. Przy dostępie z PBOX1/Claude Cloud/ChatGPT trzeba **osobno potwierdzić** instalację w danym kliencie; dostępność pośrednia LC MultiHost nie jest dowodem odrębnego MCP.

Kanoniczny kod i ograniczenia schematu są utrzymywane przez projekt \`chatgpt-identity-graph\`. Wersje tego pliku w repozytoriach MCP mają służyć jako instrukcja dla klienta. Nie wolno im wprowadzać konkurencyjnych lokalnych baz tożsamości. Wszystkie zmiany kodu należy testować przed wdrożeniem i zapisać w GitHub. Statusy zadania: do zrobienia / w trakcie / zrobione / zablokowane, niezależnie od miejsca zapisu kodu.

