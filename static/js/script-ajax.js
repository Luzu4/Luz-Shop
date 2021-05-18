const button = document.querySelector('#checkout-button');

button.addEventListener('click', event => {
    fetch('/stripe_pay')
    .then((result) => {return result.json();})
    .then((data) => {
        var stripe = Stripe(data.checkout_public_key);
        stripe.redirectToCheckout({
            sessionId: data.checkout_session_id
        }).then(function (result) {
        // If redirectToCheckout fails due to a browser or network
        // error, you should display the localized error message to your
        // customer using error.message.
        });
    })
});

const add_to_cart_button = document.querySelector('#add_to_cart');

add_to_cart_button.addEventListener('click', event => {
        function checkForm(){
             var form = document.forms[0];
             var selectElement = form.querySelector('input[name="pwd"]');
             var quantity = selectElement.value;
             return quantity
        }
        quantity = checkForm();
    fetch('/add_to_cart/' + quantity + '/' + price_id);
    location.reload(true);
    });
