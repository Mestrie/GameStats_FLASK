from deep_translator import GoogleTranslator

def traduzir_texto(texto, source="en", target="pt"):
    if not texto:
        return texto

    try:
        return GoogleTranslator(
            source=source,
            target=target
        ).translate(texto)
    except Exception as e:
        print("Erro ao traduzir:", e)
        return texto  # fallback
