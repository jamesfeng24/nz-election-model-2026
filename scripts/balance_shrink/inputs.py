"""Pin the consumed inputs (design, Stage48 outputs and code, inventory, scales, Stage47 ablation)."""
from .common import PREFIX, ROOT, pin, read, save, arguments, digest, INPUTS


def main():
    args = arguments()
    value = pin()
    if args.check:
        stored = read(PREFIX + '/input-contract.json')
        if stored != value:
            raise ValueError('Stale Stage60 input contract')
    else:
        save('input-contract.json', value)
    print('Stage60 input contract ' + ('verified' if args.check else 'written'))


if __name__ == '__main__':
    main()
