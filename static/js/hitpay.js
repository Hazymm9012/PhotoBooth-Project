function onSuccess (data) {
    const el = document.createElement('p')
    el.innerHTML = 'success'
    document.body.appendChild(el)
  }

  function onClose (data) {
    const el = document.createElement('p')
    el.innerHTML = 'closed'
    document.body.appendChild(el)
  }
  
  function onError (error) {
    const el = document.createElement('p')
    el.innerHTML = 'Error: ' + error
    document.body.appendChild(el)
  }

  async function onClickPay() {
    if (!window.HitPay.inited) {
      console.log('Initializing HitPay...')
      window.HitPay.init('https://securecheckout.sandbox.hit-pay.com/payment-request/@dummy-company-4',
        {
        // Optional, default is https
        // scheme: 'http',
        // Optional, default is hit-pay.com
        domain: 'sandbox.hit-pay.com',
        apiDomain: 'sandbox.hit-pay.com',
        // Optional default is false
        closeOnError: true
      },
      // Optional callbacks
      {
        onClose: onClose,
        onSuccess: onSuccess,
        onError: onError
      })
    }

    // Fetch payment request ID from backend
    const res = await fetch("/create-payment-request");
    const data = await res.json();

    window.HitPay.toggle({
      // Payment request method params
      paymentRequest: data.id,          
      // Optional
      //method: 'card',
      // Default method params
      // Optional
      amount: 100
    })          
  }