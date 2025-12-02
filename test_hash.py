from python.extensions import bcrypt

hash_salvo = "$2b$12$KCtzga4TgSMLZTjgYYjKVugN2BvLnXIlbx3O.HTOxiACFr2pRsAsO"

teste_senha = "lol13424134"

print(bcrypt.check_password_hash(hash_salvo, teste_senha))
