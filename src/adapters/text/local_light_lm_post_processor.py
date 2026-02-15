from __future__ import annotations

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


class LocalLightLMPostProcessor:
    COMMAND_HINTS: tuple[str, ...] = (
        "virgule",
        "point",
        "deux points",
        "point d interrogation",
        "point d exclamation",
        "a la ligne",
        "à la ligne",
        "retour a la ligne",
        "retour à la ligne",
        "nouveau paragraphe",
    )

    def __init__(
        self,
        model_name: str = "google/flan-t5-small",
        max_input_chars: int = 1200,
        max_new_tokens: int = 220,
    ) -> None:
        self._model_name = model_name
        self._max_input_chars = max_input_chars
        self._max_new_tokens = max_new_tokens
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    def process(self, text: str) -> str:
        if not text:
            return ""

        trimmed = text.strip()
        lowered = trimmed.lower()
        if not any(hint in lowered for hint in self.COMMAND_HINTS):
            return trimmed
        if len(trimmed) > self._max_input_chars:
            trimmed = trimmed[: self._max_input_chars]

        prompt = self._build_prompt(trimmed)

        inputs = self._tokenizer(prompt, return_tensors="pt", truncation=True)
        output_ids = self._model.generate(
            **inputs,
            max_new_tokens=self._max_new_tokens,
            do_sample=False,
            num_beams=4,
            length_penalty=0.9,
            repetition_penalty=1.1,
        )
        result = self._tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()
        return result or trimmed

    @staticmethod
    def _build_prompt(text: str) -> str:
        return (
            "Tache: post-traiter une dictee medicale en francais.\n"
            "Regles:\n"
            "- Convertir les commandes vocales en ponctuation/mise en page.\n"
            "- Exemples: 'virgule'->',' ; 'point'->'.' ; 'deux points'->':' ; "
            "'point d interrogation'->'?' ; 'point d exclamation'->'!'.\n"
            "- 'a la ligne' ou 'retour a la ligne' => saut de ligne.\n"
            "- 'nouveau paragraphe' => ligne vide entre paragraphes.\n"
            "- Si la ponctuation est deja presente, ne rien ajouter.\n"
            "- Si une commande vocale est redondante avec une ponctuation deja presente, "
            "supprimer la commande sans dupliquer le signe.\n"
            "- Interdiction de produire des doublons comme '..', ',,' , '??', '!!', '.,'\n"
            "- Ne rien inventer, ne rien resumer, garder tous les mots utiles.\n"
            "- Sortie: uniquement le texte final.\n\n"
            "Exemple 1:\n"
            "Entree: chers collegues virgule je vous adresse cette patiente point a la ligne "
            "l examen est rassurant point\n"
            "Sortie: Chers collegues, je vous adresse cette patiente.\n"
            "L'examen est rassurant.\n\n"
            "Exemple 2:\n"
            "Entree: antecedents familiaux deux points cancer du sein chez la mere a 48 ans point\n"
            "Sortie: Antecedents familiaux: cancer du sein chez la mere a 48 ans.\n\n"
            "Exemple 3:\n"
            "Entree: les cycles sont reguliers. point a la ligne l examen est normal,\n"
            "Sortie: Les cycles sont reguliers.\nL'examen est normal,\n\n"
            f"Entree:\n{text}\n\n"
            "Sortie:"
        )
