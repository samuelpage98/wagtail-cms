# To install x86 docker

```
curl https://raw.githubusercontent.com/Homebrew/homebrew-core/05d02418e00ef6e9af79018e3655536063f68ab2/Formula/q/qemu.rb -o qemu.rb
curl https://raw.githubusercontent.com/Homebrew/homebrew-core/442f9cc511ce6dfe75b96b2c83749d90dde914d2/Formula/c/capstone.rb -o capstone.rb
brew unlink qemu
brew install qemu.rb
brew unlink capstone
brew install capstone.rb
```

# To install
