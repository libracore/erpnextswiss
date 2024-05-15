// Create namespace for our example ecr
simpleEcr = {};

/**
 * Listener example that extends the DefaultTerminalListener
 */
class timapiListener extends timapi.DefaultTerminalListener {

    /**
     * Called if the state of the terminal changed. Retrieve the state using
     * terminal.getTerminalState().
     * @param {timapi.Terminal} terminal Terminal-instance that fired a status-change
     */
    terminalStatusChanged(terminal) {
        super.terminalStatusChanged(terminal);
        let terminalStatus = terminal.getTerminalStatus();
        console.log("Terminal Status: " + terminalStatus);
        updateDisplayContent(terminalStatus);
    }

    /**
     * Called by all of the other request specific methods unless they are implemented differently.
     * @param {timapi.TimEvent} event Contains the terminal sending the event and error information if the request failed.
     * @param {Object} data  Contains additional request specific data. Can be "undefined" if the request in
     *             			 question does not support any additional data. Use event.getRequestType() to determine the type of request.
     */
    requestCompleted(event, data){
        super.requestCompleted(event, data);
        console.log("Request of type "+ event.requestType + " completed...");
        if(event.exception !== undefined) {
            console.log("Exception:" + event.exception);
        }
        if(data !== undefined) {
            console.log("Request data:" + data);
        }
    }

    /**
     * Called if a request started with {@link timapi.Terminal#connectAsync connectAsync} finished.
     * @param {timapi.TimEvent} event Contains the terminal sending the event and error information if the request failed.
     */
    connectCompleted(event){
        super.connectCompleted(event);
        console.log(event);
    }

    /**
     * Called if a request started with {@link timapi.Terminal#transactionAsync transactionAsync} finished.
     * @param {timapi.TimEvent} event Contains the terminal sending the event and error information if the request failed.
     * @param {timapi.TransactionResponse} data  Contains transaction result information and print information for the merchant and cardholder.
     */
    transactionCompleted(event, data){
        super.transactionCompleted(event, data);

        // Get transaction information to extract transaction reference numbers.
        // These can be used in a following transaction e.g. in case of reversal.
        if (data != undefined && data.transactionInformation != undefined) {
            switch (data.transactionType) {
                case timapi.constants.TransactionType.reservation:
                case timapi.constants.TransactionType.adjustReservation:
                    $('#lastTransaction').val(data.transactionInformation.acqTransRef);
                    break;
                case timapi.constants.TransactionType.purchase:
                default:
                    $('#lastTransaction').val(data.transactionInformation.transSeq);
                    break;
            }
        }
    }
}

/**
 * Lads all button-events
 */
function attachButtons() {
    $("#btnPurchase").click( purchase );
    $("#btnCredit").click(credit);
    $("#btnCommit").click(commit);
    $("#btnRollblack").click(rollback);
    $("#btnReversal").click(reversal);
    $("#btnBalance").click(balance);
    $("#btnReconciliation").click(reconciliation);
    $("#btnReconfig").click(reconfig);
    $("#btnCancel").click(cancel);
    $("#btnConnect").click(connect);
    $("#btnDisconnect").click(disconnect);
    $("#btnLogout").click(logout);
    $("#btnLogin").click(login);
    $("#btnActivate").click(activate);
    $("#btnDeactivate").click(deactivate);
}

/**
 * Initalizes the tim api
 */
function initTimApi() {	
    // Create settings with IP-address and port of terminal to connect to
    let settings = new timapi.TerminalSettings();
    
    frappe.db.get_doc("Worldline TIM", "Worldline TIM").then(function(details){
        // IP-address and port of terminal to connect to
        settings.connectionIPString = details.connectionipstring;
        settings.connectionIPPort = details.connectionipport;

        // The integrator id to identify the integrator
        settings.integratorId = details.integratorid;

        // Deactivate fetch brands and auto commit
        settings.fetchBrands = false;
        settings.autoCommit = parseInt(details.autocommit) == 1 ? true:false;

        // Create terminal
        simpleEcr.terminal = new timapi.Terminal(settings);

        // Add user data
        simpleEcr.terminal.setPosId("ECR-01");
        simpleEcr.terminal.setUserId(1);

        // Add customized listener
        simpleEcr.terminal.addListener(new timapiListener());

        // Add button events
        attachButtons();
    });
}

/**
 * Disconnect from terminal
 */
function disconnect(e) {
    e.preventDefault();
    try {
        simpleEcr.terminal.disconnectAsync();
    } catch (err) {
        console.log("Error: " + err);
    }
}

/**
 * Function will be called, when timapi has a log message
 */
function onTimApiLog(message) {
    console.log(message);
    // send to log server or alike
}

/**
 * Make a purchase transaction
 */
function purchase(e) {
    e.preventDefault();
    try {
        let amount  = new timapi.Amount($('#editAmount').val(), timapi.constants.Currency.CHF)
        simpleEcr.terminal.transactionAsync(timapi.constants.TransactionType.purchase, amount);
    } catch( err ) {
        console.log("Error: " + err);
    }
}

/**
 * Update ui with terminal status data
 */
function updateDisplayContent(terminalStatus) {
    if (terminalStatus !== undefined) {
        var text = '';
        if (terminalStatus.displayContent.length > 0) {
            text = terminalStatus.displayContent[0];
        }
        $('#display-line1').text(text);
        if (text == '') {
            $('#display-line1').append('&nbsp;');
        }

        text = '';
        if (terminalStatus.displayContent.length > 1) {
            text = terminalStatus.displayContent[1];
        }
        $('#display-line2').text(text);
        if (text == '') {
            $('#display-line2').append('&nbsp;');
        }
    }
}

/**
 * Connect to terminal
 */
function connect(e) {
    e.preventDefault();
    try {
        simpleEcr.terminal.connectAsync();
    } catch (err) {
        console.log("Error: " + err);
    }
}

/**
 * Login, activate a communication session between ECR and terminal
 */
function login(e){
    e.preventDefault();
    try {
        simpleEcr.terminal.loginAsync();
    } catch( err ) {
        console.log("Error: " + err);
    }
}

/**
 * Logout, terminates an active communication session between ECR and terminal
 */
function logout(e) {
    e.preventDefault();
    try {
        simpleEcr.terminal.logoutAsync();
    } catch( err ) {
        console.log("Error: " + err);
    }
}

/**
 * Activate, opens a shift
 */
function activate(e) {
    e.preventDefault();
    try {
        simpleEcr.terminal.activateAsync();
    } catch( err ) {
        console.log("Error: " + err);
    }
}

/**
 * Deactivate, closes a shift
 */
function deactivate(e) {
    e.preventDefault();
    try {
        simpleEcr.terminal.deactivateAsync();
    } catch( err ) {
        console.log("Error: " + err);
    }
}

/**
 * Make a financial transaction of type reversal
 * Reversal can revoke a previous transaction, referenced by a transaction reference
 */
function reversal(e) {
    e.preventDefault();
    try {

        var trxData = new timapi.TransactionData();
        trxData.transSeq = $('#lastTransaction').val();
        simpleEcr.terminal.setTransactionData(trxData);

        simpleEcr.terminal.transactionAsync(timapi.constants.TransactionType.reversal, undefined);
    } catch( err ) {
        console.log("Error: " + err);
    }

}

/**
 * Make a financial transaction of type credit
 */
function credit(e) {
    e.preventDefault();
    try {
        var amount  = new timapi.Amount($('#editAmount').val(), timapi.constants.Currency.CHF)
        simpleEcr.terminal.transactionAsync(timapi.constants.TransactionType.credit, amount);
    } catch( err ) {
        console.log("Error: " + err);
    }
}

/**
 * Try to cancel a running request
 */
function cancel(e) {
    e.preventDefault();
    try {
        simpleEcr.terminal.cancel();
    } catch( err ) {
        console.log("Error: " + err);
    }
}

/**
 * Commit an authorized transaction
 */
function commit(e) {
    e.preventDefault();
    try {
        simpleEcr.terminal.commitAsync();
    } catch( err ) {
        console.log("Error: " + err);
    }
}

/**
 * Rollback an authorized transaction
 */
function rollback(e) {
    e.preventDefault();
    try {
        simpleEcr.terminal.rollbackAsync();
    } catch( err ) {
        console.log("Error: " + err);
    }
}

/**
 * Request balance
 */
function balance(e) {
    e.preventDefault();
    try {
        simpleEcr.terminal.balanceAsync();
    } catch( err ) {
        console.log("Error: " + err);
    }
}

/**
 * Request reconfiguration
 */
function reconfig(e) {
    e.preventDefault();
    try {
        simpleEcr.terminal.reconfigAsync();
    } catch (err) {
        console.log("Error: " + err);
    }
}

/**
 * Request reconciliation
 */
function reconciliation(e) {
    e.preventDefault();
    try {
        simpleEcr.terminal.reconciliationAsync();
    } catch (err) {
        console.log("Error: " + err);
    }
}

// init tim api after loading this script
initTimApi();
