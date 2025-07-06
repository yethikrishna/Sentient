<p align="center"><img src="https://i.imgur.com/X7dSE68.png"></p>

## Next.js Web Client

This is a Next.js project bootstrapped with [`create-next-app`](https://github.com/vercel/next.js/tree/canary/packages/create-next-app).

## Usage

### Install Dependencies

First, ensure you have Node.js and a package manager (npm, yarn, or pnpm) installed.

If you have a `package-lock.json` from the old Electron project, delete it and the `node_modules` directory:

```bash
$ rm -rf node_modules package-lock.json
```

Then, install the dependencies:

```
# using yarn or npm
$ yarn (or `npm install`)

# using pnpm
$ pnpm install --shamefully-hoist
```

### Use it

```
# development mode
$ yarn dev (or `npm run dev` or `pnpm run dev`)

# production build
$ yarn build (or `npm run build` or `pnpm run build`)
```
