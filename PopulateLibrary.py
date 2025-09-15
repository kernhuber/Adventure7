#
# Ein kleines Tool zur Erzeugung von lustigen Buchtiteln für die Bibliothek des Adventures
#
from __future__ import annotations

import google.generativeai as genai
import os
import json # Für strukturierte Prompts/Antworten/Funktionsaufrufe
from pprint import pprint
from Utils import dprint, dpprint, dl, ddiff
from google.api_core import retry
import os
from dotenv import load_dotenv

# Konfiguration der Gemini API mit deinem API-Schlüssel
# Es wird dringend empfohlen, den API-Schlüssel nicht direkt im Code zu speichern!
# Besser: Als Umgebungsvariable setzen (z.B. GEMINI_API_KEY)
# genai.configure(api_key="DEIN_API_KEY_HIER_ODER_AUS_UMGEBUNGSVARIABLE")
# Alternativ:

class GenerateBookTitles:
    #
    # Create Random Book Titles for Library
    #
    def  __init__(self):
        apikey = os.environ.get("GOOGLE_API_KEY",None)
        if not apikey:
            load_dotenv("apikey.env")
            apikey = os.getenv("GOOGLE_API_KEY")  # Ausgabe: bar

        genai.configure(api_key=apikey)
        #
        # Retry-Mechanismus
        #
        is_retriable = lambda e: (isinstance(e, genai.errors.APIError) and e.code in {429, 503})
        genai.GenerativeModel.generate_content = retry.Retry(
            predicate=is_retriable
        )(genai.GenerativeModel.generate_content)

# Globale Model-Instanzen, die wir wiederverwenden können
# Wir könnten verschiedene Modelle für verschiedene Aufgaben nutzen, z.B. Flash für schnelle Parser, Pro für Reasoning
        self.gemini_text_model = genai.GenerativeModel('gemini-1.5-flash') # Gut für schnelle Textgenerierung/Parsing
        self.tokens = 0
        self.numcalls = 0
        self.token_details = []



    import json
    from typing import List, Dict, Any


    def new_book(self):






        prompt_str = f"""

In einem Adventure-Spiel gibt es eine Bibliothek mit wissenschaftlichen, pseudowissenschaftlichen und leicht versponnenen Büchern und Papers.
Das Adventure spielt in einer abgelegenen Wüstenstadt in den 1980er Jahren, und offenbar hat ein verrückter Wissenschaftler wundersame
Maschinen konstruiert, die mit Elektrizität funktionieren, und Tore zu anderen Dimensionen öffnen können. Dazu benötigt er Literatur
aus vielfältigen wissenschaftlichen Disziplinen wie Physik, Chemie, Mathematik, Informatik, Biologie, Astronomie, Geographie. Er hat aber
auch alte Folianten, die sich mit Esoterik, Astrologie, Zauberei und jenseitigen Welten beschäftigen, gelesen. Auch Bücher über vergessene
Religionen und alte Rituale zur Beschörung von Geistern und Dämonen waren wichtig.

Erzeuge eine Liste von 100 Büchern in diesem Kontext, die als Objekte in dem Adventure verwendet werden können. Jedes Buch denkst Du dir
folgendes aus:

* Einen Titel: Etwas Verschwurbeltes aus oben genannten Themenbereichen, was sich aber sehr wissenschaftlic anhört
* Autoren: ein bis fünf Autoren samt deren akademischen Titeln. Ein Autor kann, aber muss keinen akademischen Titel aufweisen. Erzeuge nur fiktive Namen, keinesfalls Namen bekannter Persönlichkeiten!
* Abstract: ein kurzer Text (maximal 200 Zeichen), der den Inhalt des Werkes beschreibt. Beziehe den Inhalt auf den gewählten Titel
* Erscheinungsort: Ort kann frei gewählt werden, sollte aber eine Universitätsstadt sein
* Erscheinungsjahr: sollte irgendwie zum Titel passen - ein Buch über Alchemie kann zum Beispiel aus dem Mittelalter stammen, eins über Computertechnik sollte aus dem 20. Jahrhundert stammen 
* Verleger: Ein frei erfundener Verlag, der sich aber sehr wissenschaftlich anhört

Die Texte, Namen und Titel sollen etwas zum schmunzeln sein. Sie richten sich an jugendliche Spieler des Adventures aus den 1980er Jahren


Regeln (wichtig):
- Antworte ausschließlich mit JSON, ohne Codefences, ohne Fließtext.
- Verwende in Werten niemals doppelte Anführungszeichen. Spitznamen in Klammern. Beispiel: Gertrud (Trudy) Zauber.
- Struktur exakt wie im Beispiel (authors ist ein String, abstract ≤ 200 Zeichen).

Beispiel:

```json
[
  {{"book": {{"title": "<Buchtitel1>", "authors":"<Autoren1>", "abstract":"<Abstract1>", "release_loc":"<Erscheinungsort1>", "release_date": "<Erscheinungjahr1>", "released_by":"<Verleger1>"}}}},
  {{"book": {{"title": "<Buchtitel2>", "authors":"<Autoren2>", "abstract":"<Abstract1>", "release_loc":"<Erscheinungsort1>", "release_date": "<Erscheinungjahr1>", "released_by":"<Verleger1>"}}}},

]
```
            """

        try:
            import google.generativeai as genai
            # from google.generativeai.types import GenerationConfig, Tool  # Füge Tool hinzu!
            from google.generativeai.client import get_default_retriever_client

            my_generation_config = genai.types.GenerationConfig(
                    # max_output_tokens=150,
                    response_mime_type="application/json"  # Hier fordern wir JSON an
                )

            response = self.gemini_text_model.generate_content(
                contents=prompt_str,
                generation_config= my_generation_config
            )


            dprint(dl.LLM, "LLM-Info: ++++++++++++++")
            dprint(dl.LLM_PROMPT,prompt_str)
            dprint(dl.LLM_PROMPT,"+++++++ END OF PROMPT +++++++")
            dprint(dl.LLM,
                   f"LLM Raw Response: {response.text}")  # response.text kann auch leer sein, wenn nur tool_calls



            # Durchlaufe die generierten Kandidaten (normalerweise nur einer)
            if response.text:
                r = json.loads(response.text)
                dprint(dl.LLM, "JSON Output:-------")
                dpprint(dl.LLM, r)

                # Token-Nutzung aktualisieren
                self.tokens += response.usage_metadata.total_token_count
                self.numcalls += 1
                self.token_details.append(response.usage_metadata.total_token_count)
                return r
            else:
                dprint(dl.LLM, "WARNING: No candidates generated by LLM.")
                return []






        except Exception as e:
            # Hier fangen wir jegliche JSONDecodeError oder andere Exceptions ab
            # Versuche, die rohe Antwort des LLM zu loggen, auch wenn sie ungültiges JSON war
            if 'response' in locals() and hasattr(response, 'text'):
                dprint(dl.LLM, f"LLM Raw Response (possibly malformed): {response.text}")
            if 'response' in locals():
                dprint(dl.LLM, "response:")
                dpprint(dl.LLM,response)
            else:
                dprint(dl.LLM,"LLM did not send a response")
            dprint(dl.LLM, f"Prompt used: {prompt_str}")


            # Bei einem Fehler geben wir einen 'zurueckweisen'-Befehl als Dictionary zurück
            return []


#
#  Main Function
#

gen = GenerateBookTitles()
books = gen.new_book()

with open("books.json", "w", encoding="utf-8") as f:
    json.dump(books, f, ensure_ascii=False, indent=2, sort_keys=True)