
const testStrings = [
    'Each square inside the shape is counted from 1 to 7." class="max-w-full h-auto rounded-lg" style="max-width: 216px; max-height: 216px;" />',
    '![A shape with 4 sides...](web+graphie://...) class="max-w-full h-auto rounded-lg" style="max-width: 216px; max-height: 216px;" />'
];

const regex = /!\[([^\]]*)\]\(([^)]+)\)[^>]*>/g;

testStrings.forEach(s => {
    console.log('--- Testing string ---');
    console.log('Original:', s);

    const replaced = s.replace(regex, (_, alt, url) => {
        console.log('Match found!');
        console.log('Alt:', alt);
        console.log('Url:', url);
        return '[IMAGE_REPLACED]';
    });

    console.log('Result:', replaced);
});
