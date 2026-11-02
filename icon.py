from PIL import Image


# Carrega a imagem PNG que você salvou
print("Carrega imagem original")
imagem = Image.open('downloader.png')

# Salva como .ico com múltiplos tamanhos (boa prática para ícones de janela)
imagem.save('downloader.ico', format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

print("Ícone downloader.ico gerado com sucesso!")