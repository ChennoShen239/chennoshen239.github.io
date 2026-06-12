# chennoshen239.github.io

Personal academic website, built with [Quarto](https://quarto.org).

## Edit & publish

```sh
quarto preview            # local preview
quarto publish gh-pages   # render + deploy
```

## Replace the profile photo

Drop a square-ish photo at `img/profile.jpg`, then in `index.qmd` change
`image: img/profile.svg` to `image: img/profile.jpg`.

## Deploy 

```sh
cd ~/Dropbox/Website/chennoshen239.github.io
git add -A && git commit -m "update" && git push   
quarto publish gh-pages --no-prompt             
```