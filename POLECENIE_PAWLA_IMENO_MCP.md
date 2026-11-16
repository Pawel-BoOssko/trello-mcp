# Polecenie Pawła — programiści projektów MCP (16.11.2026)

**Adresat: programista / agent rozwijający TEN projekt.** Nie jest to bieżące polecenie dla czatu korzystającego z narzędzi MCP i nie nakazuje teraz uruchamiać synchronizacji.

Jeżeli ten projekt obejmuje **rejestrację czatów przez MCP** lub **synchronizację danych/tożsamości czatów**, to przed jakimikolwiek zmianami w tym obszarze należy **podjąć z Pawłem wspólną pracę nad uzgodnieniem**:

1. Docelowego przeniesienia całej rejestracji oraz dwukierunkowej synchronizacji danych/tożsamości czatu do centralnego projektu **IMENO**, zamiast utrzymywania tych mechanizmów w poszczególnych serwerach MCP.
2. Docelowego przekazywania przez każdy serwer MCP **raz na sesję, przed rozpoczęciem właściwej pracy**, instrukcji dla czatu, aby użył centralnego polecenia synchronizacji IMENO (a gdy brak rejestracji — Rejestratora IMENO).
3. Pozostawienia serwerowi MCP wyłącznie obowiązku przekazania tej instrukcji; bez samodzielnej synchronizacji i bez weryfikowania, czy czat wykonał polecenie.
4. Bezpiecznej migracji istniejących rozwiązań, z zachowaniem działania obecnego Rejestratora do czasu decyzji Pawła. **Przejściowo dwa niezależne rejestratory są dopuszczalne.**

**Nie przeprowadzać migracji, nie usuwać istniejącej rejestracji i nie zmieniać zachowania MCP na podstawie tego dokumentu bez uprzedniej rozmowy z Pawłem.** Polecenie ma zostać zauważone przez programistę przy następnej pracy nad odpowiednim obszarem projektu.

Źródło: bezpośrednie polecenie Pawła, 16.11.2026. Właścicielem planowanej architektury centralnej jest projekt IMENO. 
